use super::fromalt::FromAlt;
use blake2::{digest::generic_array::GenericArray, Digest};
use codec::{Decode, Encode};
use core::{fmt::Debug, marker::PhantomData};
use derivative::Derivative;

pub trait Hash {
    fn hash<D: Digest>(&self, hasher: &mut D);
}

impl<T: Hash> Hash for [T] {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        for s in self {
            s.hash(hasher);
        }
    }
}

impl<T: Hash> Hash for [T; 8] {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        let a: &[T] = self.as_ref();
        a.hash(hasher);
    }
}

impl<T: Hash> Hash for [T; 32] {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        let a: &[T] = self.as_ref();
        a.hash(hasher);
    }
}

impl<A: Hash + ?Sized> Hash for &A {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        (**self).hash(hasher);
    }
}

impl<A: Hash, B: Hash> Hash for (A, B) {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        self.0.hash(hasher);
        self.1.hash(hasher);
    }
}

impl<A: Hash, B: Hash, C: Hash> Hash for (A, B, C) {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        self.0.hash(hasher);
        self.1.hash(hasher);
        self.2.hash(hasher);
    }
}

impl<A: Hash, B: Hash, C: Hash, D: Hash> Hash for (A, B, C, D) {
    fn hash<H: Digest>(&self, hasher: &mut H) {
        self.0.hash(hasher);
        self.1.hash(hasher);
        self.2.hash(hasher);
        self.3.hash(hasher);
    }
}

impl Hash for u8 {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        hasher.input([*self]);
    }
}

#[derive(Encode, Decode, Derivative)]
#[derivative(
    Clone(bound = "Output: Clone"),
    PartialEq(bound = "Output: PartialEq"),
    Eq(bound = "Output: Eq"),
    Debug(bound = "Output: Debug"),
    Default(bound = "Output: Default")
)]
pub struct Hashed<Preimage: ?Sized, Output> {
    pub hash: Output,
    _spook: PhantomData<Preimage>,
}

impl<P, O> Hashed<P, O> {
    pub fn prehashed(hash: O) -> Self {
        let _spook = PhantomData;
        Self { hash, _spook }
    }

    pub fn from_preimage<Hasher>(preimage: &P) -> Self
    where
        Hasher: Digest,
        P: Hash,
        O: FromAlt<GenericArray<u8, Hasher::OutputSize>>,
    {
        let mut hasher = Hasher::new();
        preimage.hash(&mut hasher);
        Hashed::prehashed(O::from_alt(hasher.result()))
    }
}

impl<P, O: Hash> Hash for Hashed<P, O> {
    fn hash<D: Digest>(&self, hasher: &mut D) {
        self.hash.hash(hasher)
    }
}
