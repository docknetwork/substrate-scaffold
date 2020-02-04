//! Typechecked merkle tree operations.

use super::fromalt::FromAlt;
use super::hasher::{Hash, Hashed};
use blake2::digest::{generic_array::GenericArray, Digest};
use codec::{Decode, Encode};
use core::{fmt::Debug, marker::PhantomData};
use derivative::Derivative;

#[derive(Encode, Decode, Derivative)]
#[derivative(
    Clone(bound = "O: Clone"),
    PartialEq(bound = "O: PartialEq"),
    Eq(bound = "O: Eq"),
    Debug(bound = "O: Debug"),
    // Default makes sense in this context, A default MerkleRoot represents
    // a Root with no possible leaves. Since nothing hashes to [0u8; 32],
    // there are no valid proofs of inclusion in the default.
    Default(bound = "O: Default"),
)]
pub struct MerkleRoot<T, O> {
    hash: O,
    _spook: PhantomData<T>,
}

impl<T, O> MerkleRoot<T, O> {
    pub fn from_root(hash: O) -> Self {
        let _spook = PhantomData;
        Self { hash, _spook }
    }
}

#[derive(Encode, Decode, Clone, Debug, PartialEq, Eq)]
pub enum ProofElement<O> {
    Left(O),
    Right(O),
}

impl<O> ProofElement<O> {
    /// Concatentate self with sibling in the proper order and return the hash.
    fn merge<H>(&self, sibling: &O) -> O
    where
        H: Digest,
        O: Hash + FromAlt<GenericArray<u8, H::OutputSize>>,
    {
        let (a, b) = match self {
            ProofElement::Left(h) => (h, sibling),
            ProofElement::Right(h) => (sibling, h),
        };
        Hashed::from_preimage::<H>(&(a, b)).hash
    }
}

pub fn verify_proof<H, T, O>(
    root: &MerkleRoot<T, O>,
    proof: &[ProofElement<O>],
    leafhash: &Hashed<T, O>,
) -> bool
where
    H: Digest,
    O: Hash + Eq + FromAlt<GenericArray<u8, H::OutputSize>>,
{
    let lhh: Hashed<Hashed<T, O>, O> = Hashed::from_preimage::<H>(leafhash);
    let expected_root = proof.iter().fold(lhh.hash, |leaf, pe| pe.merge::<H>(&leaf));
    expected_root == root.hash
}

#[cfg(test)]
mod test {
    use super::*;
    use blake2::Blake2s;
    use hex_literal::hex;
    use rand::distributions::{Distribution, Standard};

    /// Hash using Blake2s
    fn blash(x: impl Hash) -> [u8; 32] {
        Hashed::from_preimage::<Blake2s>(&x).hash
    }

    fn static_assert_impls(_: impl Encode + Decode + Eq + Debug) {}

    #[test]
    fn types_impl_needed_traits() {
        struct Blah {}
        #[derive(Encode, Decode)]
        struct O {}
        static_assert_impls(Hashed::<Blah, [u8; 32]>::prehashed([0u8; 32]));
        static_assert_impls(MerkleRoot::<Blah, [u8; 32]>::from_root([0u8; 32]));
        static_assert_impls(ProofElement::<[u8; 32]>::Left([0u8; 32]));
    }

    enum MTree<HashOut> {
        Leaf(HashOut),
        Tee(Box<MTree<HashOut>>, Box<MTree<HashOut>>),
    }

    impl<HashOut> MTree<HashOut> {
        /// create a random Merkle tree with 2^(depth+1)-1 nodes
        fn generate(depth: u8) -> Self
        where
            Standard: Distribution<HashOut>,
        {
            debug_assert!(depth < 36, "would require ~2TB of memory",);
            match depth.checked_sub(1) {
                None => MTree::Leaf(rand::random()),
                Some(d) => MTree::Tee(Box::new(Self::generate(d)), Box::new(Self::generate(d))),
            }
        }

        fn root_hash<H>(&self) -> HashOut
        where
            H: Digest,
            HashOut: Hash + FromAlt<GenericArray<u8, H::OutputSize>>,
        {
            match self {
                MTree::Leaf(h) => Hashed::from_preimage::<H>(h).hash,
                MTree::Tee(left, right) => {
                    Hashed::from_preimage::<H>(&(left.root_hash::<H>(), right.root_hash::<H>()))
                        .hash
                }
            }
        }

        fn random_proof<H>(&self) -> (Vec<ProofElement<HashOut>>, &HashOut)
        where
            H: Digest,
            HashOut: Hash + FromAlt<GenericArray<u8, H::OutputSize>>,
        {
            fn rp<'tree, H, HashOut>(
                tree: &'tree MTree<HashOut>,
                ret: &mut Vec<ProofElement<HashOut>>,
            ) -> &'tree HashOut
            where
                H: Digest,
                HashOut: Hash + FromAlt<GenericArray<u8, H::OutputSize>>,
            {
                match tree {
                    MTree::Leaf(h) => h,
                    MTree::Tee(left, right) => {
                        if rand::random::<bool>() {
                            ret.push(ProofElement::<HashOut>::Right(right.root_hash::<H>()));
                            rp::<H, _>(left, ret)
                        } else {
                            ret.push(ProofElement::<HashOut>::Left(left.root_hash::<H>()));
                            rp::<H, _>(right, ret)
                        }
                    }
                }
            }
            let mut ret = Vec::new();
            let leaf = rp::<H, HashOut>(self, &mut ret);
            ret.reverse();
            (ret, leaf)
        }
    }

    #[test]
    fn manual_root() {
        type Blake2sHash = [u8; 32];
        use blash as hash;
        fn cash(a: impl Hash, b: impl Hash) -> Blake2sHash {
            hash(&(a, b))
        }

        {
            let a = rand::random();
            let b = rand::random();
            let c = rand::random();
            let tree = MTree::<Blake2sHash>::Tee(
                Box::new(MTree::Tee(
                    Box::new(MTree::Leaf(a)),
                    Box::new(MTree::Leaf(b)),
                )),
                Box::new(MTree::Leaf(c)),
            );
            assert!(tree.root_hash::<Blake2s>() != cash(cash(a, b), hash(c)));
            assert!(tree.root_hash::<Blake2s>() == cash(cash(hash(a), hash(b)), hash(c)));
        }
        {
            let a = b"{\"document\": 1}";
            let b = b"{\"document\": 2}";
            let c = b"{\"document\": 3}";
            let (ah, bh, ch) = (hash(&a[..]), hash(&b[..]), hash(&c[..]));
            let tree = MTree::Tee(
                Box::new(MTree::Tee(
                    Box::new(MTree::Leaf(ah)),
                    Box::new(MTree::Leaf(bh)),
                )),
                Box::new(MTree::Leaf(ch)),
            );
            let rh = tree.root_hash::<Blake2s>();
            assert!(rh != cash(cash(ah, bh), ch));
            assert!(rh == cash(cash(hash(ah), hash(bh)), hash(ch)));
        }
    }

    #[test]
    fn generate_and_verify_proof() {
        let tree = MTree::<[u8; 32]>::generate(4);
        let (proof, leaf) = tree.random_proof::<Blake2s>();
        let leaf = Hashed::<(), _>::prehashed(*leaf);
        let root = MerkleRoot::from_root(tree.root_hash::<Blake2s>());
        assert!(verify_proof::<Blake2s, _, _>(&root, &proof, &leaf));
    }

    #[test]
    fn invalid_proof() {
        use sha2::Sha256;
        let root = hex!("ce5215bfb7de8d9fc223852ef455c8161d256380e927b8792468124a67edc285");
        let proof = [
            ProofElement::Right(hex!(
                "394927388eb0a8ad4fa2abee5774e0a76978c34e0991d5dbfd8d57c9c63fc3a3"
            )),
            ProofElement::Right(hex!(
                "c53ab8ae5cd3402147acd585cf82273f354669bb0fbb7017ffb1a2d4e96a1fb9"
            )),
        ];
        let leaf = hex!("4741a0e50f977e1deffd81f392720a1fa152d6957e7ac5cad4d9a1631e5d278a");
        assert!(verify_proof::<Sha256, _, _>(
            &MerkleRoot::<(), _>::from_root(root),
            &proof[1..],
            &Hashed::<(), _>::prehashed(leaf)
        ));
        assert!(!verify_proof::<Blake2s, _, _>(
            &MerkleRoot::<(), _>::from_root(root),
            &proof[..],
            &Hashed::<(), _>::prehashed(leaf)
        ));
        assert!(!verify_proof::<Sha256, _, _>(
            &MerkleRoot::<(), _>::from_root(root),
            &proof[..],
            &Hashed::<(), _>::prehashed(leaf)
        ));
    }

    #[test]
    fn test_cat_hash() {
        /// hash using sha256
        fn sha(x: impl Hash) -> [u8; 32] {
            Hashed::from_preimage::<sha2::Sha256>(&x).hash
        }

        assert!(
            sha(hex!(
                "4741a0e50f977e1deffd81f392720a1fa152d6957e7ac5cad4d9a1631e5d278a"
            )) == hex!("fed1809397b63f5b8b3803c44377ad6fd233251337a71bc4c95d929156377d4e")
        );
        assert!(
            sha((
                hex!("4741a0e50f977e1deffd81f392720a1fa152d6957e7ac5cad4d9a1631e5d278a"),
                hex!("4741a0e50f977e1deffd81f392720a1fa152d6957e7ac5cad4d9a1631e5d278a")
            )) == hex!("3aaeb2f04ead632abd7587faf3ad90d6b8e3347bd08e4cd4b62f765e54c2cd9e")
        );
        assert!(
            sha((
                &[0u8; 0][..],
                hex!("4741a0e50f977e1deffd81f392720a1fa152d6957e7ac5cad4d9a1631e5d278a"),
            )) == hex!("fed1809397b63f5b8b3803c44377ad6fd233251337a71bc4c95d929156377d4e")
        );
        assert!(
            sha((
                hex!("4741a0e50f977e1d"),
                hex!("effd81f392720a1f"),
                hex!("a152d6957e7ac5ca"),
                hex!("d4d9a1631e5d278a"),
            )) == hex!("fed1809397b63f5b8b3803c44377ad6fd233251337a71bc4c95d929156377d4e")
        );
        assert!(
            sha(&b"hello hello"[..])
                == hex!("20d0bfe91d80a9f32ccf947f957582a940ab2f9998b1007511dba32f087016e0")
        );
        assert!(sha(&b"hello hello"[..]) == sha((&b"hello"[..], &b" hello"[..])));
    }
}
