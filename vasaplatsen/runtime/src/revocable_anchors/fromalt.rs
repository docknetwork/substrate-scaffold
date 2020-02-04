/// Sometimes its not possible to specify a `Into` bound.
/// Sometimes from is not implemented, but Into is.
/// This niche trait, when implemented for type `S`,
/// proves that `S` can be converted to `A` using Into::into.
pub trait FromAlt<A>: Sized + private::Sealed<A> {
    fn from_alt(other: A) -> Self;
}

impl<A, B> FromAlt<A> for B
where
    A: Into<B>,
{
    fn from_alt(other: A) -> Self {
        other.into()
    }
}

mod private {
    pub trait Sealed<A> {}
    impl<A, B> Sealed<A> for B where A: Into<B> {}
}
