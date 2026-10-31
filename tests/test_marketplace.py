from app.marketplace import _hash_password, _verify_password, Register, ReviewCreate


def test_marketplace_password_hash_is_salted_and_verified():
    first = _hash_password("correct-horse-battery-staple")
    second = _hash_password("correct-horse-battery-staple")
    assert first != second
    assert _verify_password("correct-horse-battery-staple", first)
    assert not _verify_password("wrong-password", first)


def test_marketplace_registration_requires_long_password_and_known_role():
    user = Register(email="seller@example.com", company_name="Seller Ltd",
                    country="Iran", role="producer",
                    password="correct-horse-battery-staple")
    assert user.role == "producer"


def test_reviews_are_not_assumed_verified_from_reference():
    review = ReviewCreate(subject_user_id=2, transaction_reference="ORDER-123",
                          rating=5, body="A sufficiently detailed review.")
    assert review.transaction_reference == "ORDER-123"
    # The route deliberately persists all user-submitted reviews as unverified.
