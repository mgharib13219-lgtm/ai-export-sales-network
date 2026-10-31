from app.marketplace_matching import rank_listings_for_request, score_listing_for_request


def test_exact_category_and_shared_specification_rank_higher():
    request = {"category": "dried fruit", "title": "Golden raisins",
               "specification": "golden raisins seedless grade A", "destination": "Germany",
               "quantity": "10 tonnes"}
    strong = {"id": 1, "category": "dried fruit", "name": "Seedless golden raisins",
              "description": "Grade A golden raisins", "origin": "Iran",
              "capacity": "20 tonnes", "moq": "1 tonne", "company_name": "Supplier A"}
    weak = {"id": 2, "category": "machinery", "name": "Industrial pump",
            "description": "Water pump", "origin": "Italy", "company_name": "Supplier B"}
    ranked = rank_listings_for_request(request, [weak, strong])
    assert [item["listing_id"] for item in ranked] == [1, 2]
    assert ranked[0]["score"] > ranked[1]["score"]


def test_missing_information_and_verification_holds_are_never_hidden():
    result = score_listing_for_request(
        {"category": "food", "title": "Honey", "specification": "raw honey", "destination": "France"},
        {"id": 7, "category": "food", "name": "Raw honey", "description": "Raw honey"}
    )
    assert result["status"] == "discovery_candidate_needs_human_review"
    assert result["automatically_cleared"] is False
    assert "supplier_identity_not_independently_verified" in result["mandatory_holds"]
    assert "capacity" in " ".join(result["information_gaps"])
    assert "minimum order quantity" in " ".join(result["information_gaps"])


def test_empty_or_unrelated_text_does_not_create_a_false_positive_score():
    result = score_listing_for_request(
        {"category": "chemicals", "title": "Xylene", "specification": "industrial solvent"},
        {"id": 9, "category": "textiles", "name": "Cotton shirt", "description": "woven apparel"}
    )
    assert result["score"] == 0
    assert result["reasons"] == []

def test_match_results_are_bounded_and_do_not_invent_capacity():
    request = {"category": "food", "title": "Rice", "specification": "long grain rice"}
    listings = [
        {"id": i, "category": "food", "name": "Rice", "description": "long grain rice"}
        for i in range(120)
    ]
    ranked = rank_listings_for_request(request, listings, limit=1000)
    assert len(ranked) == 100
    assert all("capacity" in " ".join(item["information_gaps"]) for item in ranked)
    assert all(item["automatically_cleared"] is False for item in ranked)
