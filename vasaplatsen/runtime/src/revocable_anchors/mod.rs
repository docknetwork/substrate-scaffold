#![cfg_attr(not(feature = "std"), no_std)]

pub mod fromalt;
pub mod hasher;
pub mod merkle;

extern crate alloc;

use alloc::vec::Vec;
use blake2::digest::{generic_array::GenericArray, Digest};
use codec::{Decode, Encode};
use core::fmt::Debug;
use frame_support::{
    decl_event, decl_module, decl_storage, dispatch::DispatchResult, ensure, Parameter, StorageMap,
};
use fromalt::FromAlt;
use hasher::{Hash, Hashed};
use merkle::{verify_proof, MerkleRoot, ProofElement};
use system::ensure_signed;

/// Max proof size for revocations.
/// This decides the number of accounts that can be authorized to revoke a root.
/// This decides the number of accounts that can be authorized to revoke a leaf.
/// max_revokers = 2 ** MAX_PROOF_SIZE
// Active question: Can we remove this limit without making the chain
// attackable?
pub const MAX_PROOF_SIZE: usize = 16;

/// The output of the hash function used constructing merkle roots configurable.
/// By default it is the the output specified in system::Trait.
pub trait Trait: system::Trait {
    type Event: From<Event<Self>> + Into<<Self as system::Trait>::Event>;

    /// The hasher used when constructing and verifying Merkle proofs.
    type TreeHash: Digest;

    /// Representation of a hash from TreeHash
    type TreeHashOut: Parameter
        + Encode
        + Decode
        + Default
        + Hash
        + FromAlt<GenericArray<u8, <Self::TreeHash as Digest>::OutputSize>>;

    /// hash Self::AccountId using Self::Treehash
    fn hash_account_id(account: &Self::AccountId, hasher: &mut Self::TreeHash);
}

/// Some arbitrary hashable thing. Only used for typechecking.
type Document = ();
/// u64::max() is around 584_942_417_355 years in the future.
pub type UnixTimeSeconds = u64;
#[derive(Encode, Decode, Debug, PartialEq, Eq, Clone)]
pub enum Revokable<T> {
    NotRevoked(T),
    Revoked,
}

decl_storage! {
    trait Store for Module<T: Trait> as TemplateModule {
        /// Scoping Anchors to the parties with revocation permission prevents frontrunning
        /// attacks.
        /// When a party proves their membership in "Administrators", they may revoke this anchor.
        Anchors: map (
            MerkleRoot<T::AccountId, T::TreeHashOut>, // Administrators
            MerkleRoot<Document, T::TreeHashOut>
        ) => Option<Revokable<T::BlockNumber>>;

        /// Suspensions mapped to suspension expiration.
        /// Setting suspension expiration to u64::max() is a permanent revocation.
        /// A party needs to prove their membership in "Administrators" in order to issue a
        /// suspension.
        ///
        /// Suspension will be active until `current_time() < suspension_end`.
        /// If `current_time() == suspension_end`, then suspension is still active.
        /// For example, if `current_time() == u64::max() == suspension_end`, the leaf is still
        /// considered suspended.
        SuspendedLeaves: map (
            MerkleRoot<T::AccountId, T::TreeHashOut>, // Administrators
            Hashed<Document, T::TreeHashOut>
        ) => Option<UnixTimeSeconds>;
    }
}

decl_module! {
    pub struct Module<T: Trait> for enum Call where origin: T::Origin {
        fn deposit_event() = default;

        /// Anyone who can prove their membership in the set represented by `admins` is authorized
        /// to permanently revoke this anchor.
        ///
        /// If `admins` represents the empty set, the anchor is irrevokable. In other words,
        /// if `admins` is a hash consisting of all zeros, the anchor is irrevokable.
        fn create_anchor(
            origin,
            admins: MerkleRoot<T::AccountId, T::TreeHashOut>,
            root: MerkleRoot<Document, T::TreeHashOut>
        ) -> DispatchResult {
            ensure_signed(origin)?; // Is this needed?
            let key = (admins, root);
            ensure!(!Anchors::<T>::exists(&key), "The root has already been anchored.");
            Anchors::<T>::insert(
                &key,
                Revokable::NotRevoked(<system::Module<T>>::block_number()),
            );
            Ok(())
        }

        /// An anchor can be revoked even before it is posted.
        fn revoke_anchor(
            origin,
            admins: MerkleRoot<T::AccountId, T::TreeHashOut>,
            root: MerkleRoot<Document, T::TreeHashOut>,
            proof: Vec<ProofElement<T::TreeHashOut>>,
        ) -> DispatchResult {
            let sender = ensure_signed(origin)?;
            ensure!(proof.len() <= MAX_PROOF_SIZE, "proof too long");
            let key = (admins.clone(), root);
            ensure!(Anchors::<T>::get(&key) != Some(Revokable::Revoked), "anchor already revoked");
            let valid = verify_proof::<T::TreeHash, T::AccountId, T::TreeHashOut>(
                &admins,
                &proof,
                &hash_account_id::<T>(&sender),
            );
            ensure!(valid, "invalid proof");
            Anchors::<T>::insert(&key, Revokable::Revoked);
            Ok(())
        }

        /// revoke leaf until suspend_end. If suspend_end is in the past, this has no sematic
        /// effect. Using u64::max() for suspend_end is a permanent revocation.
        ///
        /// This is independent of the anchor since we don't have/keep leaf data on-chain.
        ///
        /// The presence of a suspension in chain-state indicates that a member of the `admins`
        /// did suspend the 'leaf' until suspend_end.
        pub fn suspend_leaf(
            origin,
            admins: MerkleRoot<T::AccountId, T::TreeHashOut>,
            leaf: Hashed<Document, T::TreeHashOut>,
            proof: Vec<ProofElement<T::TreeHashOut>>,
            suspend_end: UnixTimeSeconds,
        ) -> DispatchResult {
            let sender = ensure_signed(origin)?;
            ensure!(proof.len() <= MAX_PROOF_SIZE, "proof too long");
            let key = (admins.clone(), leaf);
            let current_suspend_end = SuspendedLeaves::<T>::get(&key);
            if let Some(end) = current_suspend_end {
                ensure!(suspend_end > end, "leaf is already suspended until specified time");
            }
            let valid = verify_proof::<T::TreeHash, T::AccountId, T::TreeHashOut>(
                &admins,
                &proof,
                &hash_account_id::<T>(&sender)
            );
            ensure!(valid, "invalid proof");
            SuspendedLeaves::<T>::insert(key, suspend_end);
            Ok(())
        }
    }
}

fn hash_account_id<T: Trait>(
    preimage: &<T as system::Trait>::AccountId,
) -> Hashed<<T as system::Trait>::AccountId, T::TreeHashOut> {
    let mut hasher = T::TreeHash::new();
    T::hash_account_id(&preimage, &mut hasher);
    Hashed::prehashed(T::TreeHashOut::from_alt(hasher.result()))
}

impl<T: Trait> Module<T> {
    #[cfg(test)]
    pub fn lookup_anchor(
        auths: &MerkleRoot<T::AccountId, T::TreeHashOut>,
        root: &MerkleRoot<Document, T::TreeHashOut>,
    ) -> Option<Revokable<T::BlockNumber>> {
        Anchors::<T>::get((auths, root))
    }

    /// Check if there is an active suspension on `leaf` issued by the the `auths` set.
    /// Only members of the `auths` set with proof of membership may issue such a suspension.
    #[cfg(test)]
    pub fn leaf_suspended_by(
        auths: &MerkleRoot<T::AccountId, T::TreeHashOut>,
        leaf: &Hashed<Document, T::TreeHashOut>,
        now: UnixTimeSeconds,
    ) -> bool {
        match SuspendedLeaves::<T>::get((auths, leaf)) {
            None => false,
            Some(suspension_end) => now <= suspension_end,
        }
    }
}

decl_event!(
    pub enum Event<T>
    where
        <T as system::Trait>::AccountId,
    {
        Dummy(AccountId),
    }
);

/// tests for this pallet
#[cfg(test)]
mod tests {
    use super::*;
    use blake2::Blake2s;
    use frame_support::{impl_outer_origin, parameter_types, weights::Weight};
    use sp_core::H256;
    use sp_runtime::{
        testing::Header,
        traits::{BlakeTwo256, IdentityLookup},
        Perbill,
    };

    // Test module shorthand
    type Tm = Module<Test>;

    impl_outer_origin! {
        pub enum Origin for Test {}
    }

    /// Hash using Blake2s
    fn blake(x: impl Hash) -> [u8; 32] {
        Hashed::from_preimage::<Blake2s>(&x).hash
    }

    // For testing the pallet, we construct most of a mock runtime. This means
    // first constructing a configuration type (`Test`) which `impl`s each of the
    // configuration traits of modules we want to use.
    #[derive(Clone, Eq, PartialEq)]
    pub struct Test;
    parameter_types! {
        pub const BlockHashCount: u64 = 250;
        pub const MaximumBlockWeight: Weight = 1024;
        pub const MaximumBlockLength: u32 = 2 * 1024;
        pub const AvailableBlockRatio: Perbill = Perbill::from_percent(75);
    }
    impl system::Trait for Test {
        type Origin = Origin;
        type Call = ();
        type Index = u64;
        type BlockNumber = u64;
        type Hash = H256;
        type Hashing = BlakeTwo256;
        type AccountId = u64;
        type Lookup = IdentityLookup<Self::AccountId>;
        type Header = Header;
        type Event = ();
        type BlockHashCount = BlockHashCount;
        type MaximumBlockWeight = MaximumBlockWeight;
        type MaximumBlockLength = MaximumBlockLength;
        type AvailableBlockRatio = AvailableBlockRatio;
        type Version = ();
        type ModuleToIndex = ();
    }
    impl Trait for Test {
        type Event = ();
        type TreeHash = Blake2s;
        type TreeHashOut = [u8; 32];
        fn hash_account_id(account_id: &u64, hasher: &mut Blake2s) {
            hasher.input(account_id.to_be_bytes())
        }
    }
    // This function basically just builds a genesis storage key/value store according to
    // our desired mockup.
    fn new_test_ext() -> sp_io::TestExternalities {
        system::GenesisConfig::default()
            .build_storage::<Test>()
            .unwrap()
            .into()
    }

    #[test]
    fn default_values_are_none() {
        new_test_ext().execute_with(|| {
            let auth = MerkleRoot::from_root([0u8; 32]);
            let docs = MerkleRoot::from_root([0u8; 32]);
            let key = (auth, docs);
            assert!(!Anchors::<Test>::exists(&key));
            assert_eq!(Anchors::<Test>::get(&key), None);

            let auth = MerkleRoot::from_root([0u8; 32]);
            let doc = Hashed::prehashed([0u8; 32]);
            let key = (auth, doc);
            assert!(!SuspendedLeaves::<Test>::exists(&key));
            assert_eq!(SuspendedLeaves::<Test>::get(&key), None);
        });
    }

    #[test]
    fn anchor() {
        new_test_ext().execute_with(|| {
            let (auths, root) = Default::default();
            assert_eq!(Tm::lookup_anchor(&auths, &root), None);
            Tm::create_anchor(Origin::signed(0), auths.clone(), root.clone()).unwrap();
            Tm::create_anchor(Origin::signed(0), auths.clone(), root.clone())
                .expect_err("Was able to anchor twice.");
            Tm::create_anchor(Origin::signed(1), auths.clone(), root.clone())
                .expect_err("Was able to anchor twice.");
            assert_eq!(
                Tm::lookup_anchor(&auths, &root),
                Some(Revokable::NotRevoked(1))
            );

            Tm::revoke_anchor(Origin::signed(0), auths.clone(), root.clone(), vec![]).expect_err(
                "Since auths represents the empty set, the root should be irrevocable.",
            );
        });
    }

    #[test]
    fn revoke_anchor() {
        // a merkle root representing { 0u64 }
        let auths = MerkleRoot::from_root(blake(blake(&0u64.to_be_bytes()[..])));
        let docs = Default::default();

        new_test_ext().execute_with(|| {
            assert_eq!(Tm::lookup_anchor(&auths, &docs), None);
            Tm::create_anchor(Origin::signed(0), auths.clone(), docs.clone()).unwrap();
            assert_eq!(
                Tm::lookup_anchor(&auths, &docs),
                Some(Revokable::NotRevoked(1))
            );
            Tm::revoke_anchor(Origin::signed(0), auths.clone(), docs.clone(), vec![]).unwrap();
            assert_eq!(Tm::lookup_anchor(&auths, &docs), Some(Revokable::Revoked));
        });

        new_test_ext().execute_with(|| {
            Tm::revoke_anchor(Origin::signed(0), auths.clone(), docs.clone(), vec![]).unwrap();
            Tm::create_anchor(Origin::signed(0), auths.clone(), docs.clone()).unwrap_err();
        });

        new_test_ext().execute_with(|| {
            Tm::revoke_anchor(Origin::signed(0), auths.clone(), docs.clone(), vec![]).unwrap();
            Tm::revoke_anchor(Origin::signed(0), auths.clone(), docs.clone(), vec![]).unwrap_err();
        });

        new_test_ext().execute_with(|| {
            Tm::revoke_anchor(
                Origin::signed(0),
                auths.clone(),
                MerkleRoot::from_root([0; 32]),
                vec![],
            )
            .unwrap();
            Tm::revoke_anchor(
                Origin::signed(0),
                auths.clone(),
                MerkleRoot::from_root([1; 32]),
                vec![],
            )
            .unwrap();
        });
    }

    #[test]
    fn suspend_leaf() {
        // a merkle root representing { 0u64 }
        let auths = MerkleRoot::from_root(blake(blake(&0u64.to_be_bytes()[..])));
        let doc: Hashed<Document, [u8; 32]> = Default::default();

        let ua = Origin::signed(0);
        let ub = Origin::signed(1);

        new_test_ext().execute_with(|| {
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 10), false);
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 11), false);
            Tm::suspend_leaf(ua.clone(), auths.clone(), doc.clone(), vec![], 10).unwrap();
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 10), true);
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 11), false);
            Tm::suspend_leaf(ua.clone(), auths.clone(), doc.clone(), vec![], 11).unwrap();
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 10), true);
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 11), true);
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 12), false);

            // Revoke
            Tm::suspend_leaf(
                ua.clone(),
                auths.clone(),
                doc.clone(),
                vec![],
                u64::max_value(),
            )
            .unwrap();
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, 12), true);
            assert_eq!(Tm::leaf_suspended_by(&auths, &doc, u64::max_value()), true);
        });

        new_test_ext().execute_with(|| {
            Tm::suspend_leaf(ua.clone(), auths.clone(), doc.clone(), vec![], 0).unwrap();
            Tm::suspend_leaf(ua.clone(), auths.clone(), doc.clone(), vec![], 0).unwrap_err();
        });

        new_test_ext().execute_with(|| {
            Tm::suspend_leaf(ub.clone(), auths.clone(), doc.clone(), vec![], 0).unwrap_err();
        });
    }
}
