import pytest
from bookstore_trade_in import process_book_buybacks, inspect_scanner_calibration


def make_batch(fmt="paperback", books=None, approved=True, in_credit=False):
    return {
        "intake_approved": approved,
        "format": fmt,
        "payout_in_credit": in_credit,
        "books": books if books is not None else [],
    }


def make_book(condition="good", missing=0, counterfeit=False):
    return {"missing_pages": missing, "condition": condition, "counterfeit": counterfeit}


# Example test case (from starter file)
def test_single_paperback_good():
    batches = [
        {
            "intake_approved": True,
            "format": "paperback",
            "payout_in_credit": False,
            "books": [{"missing_pages": 0, "condition": "good", "counterfeit": False}]
        }
    ]
    result = process_book_buybacks(batches, 5.0)
    assert result["total_payout"] == 8.0
    assert result["status"] == "COMPLETED"


# ---------- process_book_buybacks ----------

def test_invalid_batches_type_raises():
    with pytest.raises(ValueError):
        process_book_buybacks("not a list", 5.0)


def test_unapproved_batch_is_skipped():
    result = process_book_buybacks([make_batch(approved=False, books=[make_book()])], 5.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_textbook_mint():
    result = process_book_buybacks([make_batch("textbook", [make_book("mint")])], 0.0)
    assert result["total_payout"] == 50.0
    assert result["status"] == "COMPLETED"


def test_hardcover_poor():
    result = process_book_buybacks([make_batch("hardcover", [make_book("poor")])], 0.0)
    assert result["total_payout"] == 6.0
    assert result["status"] == "COMPLETED"


def test_unknown_format_is_rejected():
    result = process_book_buybacks([make_batch("magazine", [make_book()])], 0.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_book_with_missing_pages_is_rejected():
    batches = [make_batch("paperback", [make_book(missing=3), make_book()])]
    result = process_book_buybacks(batches, 0.0)
    assert result["total_payout"] == 8.0


def test_counterfeit_textbook_wipes_batch_credit():
    batches = [make_batch("textbook", [make_book(), make_book(counterfeit=True), make_book()])]
    result = process_book_buybacks(batches, 0.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_counterfeit_paperback_only_that_book_is_dropped():
    batches = [make_batch("paperback", [make_book(counterfeit=True), make_book()])]
    result = process_book_buybacks(batches, 0.0)
    assert result["total_payout"] == 8.0


def test_payout_in_credit_adds_bonus():
    batches = [make_batch("paperback", [make_book()], in_credit=True)]
    result = process_book_buybacks(batches, 5.0)
    assert result["total_payout"] == 13.0


def test_audit_rejected_when_more_than_four_rejections():
    books = [make_book(missing=1) for _ in range(5)] + [make_book()]
    result = process_book_buybacks([make_batch("paperback", books)], 0.0)
    assert result == {"total_payout": 8.0, "status": "AUDIT_REJECTED"}


# ---------- inspect_scanner_calibration ----------

def test_scanner_no_data():
    assert inspect_scanner_calibration([]) == "NO_DATA"


def test_scanner_recalibrate_on_two_bad_readings_in_a_row():
    assert inspect_scanner_calibration([[1, 6, 7]]) == "RECALIBRATE"


def test_scanner_calibrated_when_streak_is_broken():
    assert inspect_scanner_calibration([[6, 1, 6, 1]]) == "CALIBRATED"
