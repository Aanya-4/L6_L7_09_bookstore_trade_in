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


# ---------- process_book_buybacks: input validation branches ----------

def test_invalid_batches_type_raises():
    with pytest.raises(ValueError):
        process_book_buybacks("not a list", 5.0)


def test_negative_bonus_raises():
    with pytest.raises(ValueError):
        process_book_buybacks([make_batch(books=[make_book()])], -1.0)


def test_zero_bonus_is_valid():
    result = process_book_buybacks([make_batch(in_credit=True, books=[make_book()])], 0.0)
    assert result["total_payout"] == 8.0


def test_empty_batches_list_gives_zero_credit():
    assert process_book_buybacks([], 5.0) == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


# ---------- process_book_buybacks: batch-level branches ----------

def test_unapproved_batch_is_skipped():
    result = process_book_buybacks([make_batch(approved=False, books=[make_book()])], 5.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_missing_intake_flag_defaults_to_not_approved():
    result = process_book_buybacks([{"format": "paperback", "books": [make_book()]}], 0.0)
    assert result["status"] == "ZERO_CREDIT"


def test_missing_format_defaults_to_paperback():
    result = process_book_buybacks([{"intake_approved": True, "books": [make_book()]}], 0.0)
    assert result["total_payout"] == 8.0


def test_textbook_good():
    result = process_book_buybacks([make_batch("textbook", [make_book()])], 0.0)
    assert result["total_payout"] == 40.0


def test_hardcover_good():
    result = process_book_buybacks([make_batch("hardcover", [make_book()])], 0.0)
    assert result["total_payout"] == 15.0


def test_unknown_format_is_rejected():
    result = process_book_buybacks([make_batch("magazine", [make_book()])], 0.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_empty_books_list_gives_zero_credit():
    assert process_book_buybacks([make_batch("hardcover", [])], 0.0)["status"] == "ZERO_CREDIT"


def test_missing_books_key_defaults_to_empty():
    result = process_book_buybacks([{"intake_approved": True, "format": "textbook"}], 0.0)
    assert result["status"] == "ZERO_CREDIT"


# ---------- process_book_buybacks: book-level branches ----------

def test_textbook_mint():
    result = process_book_buybacks([make_batch("textbook", [make_book("mint")])], 0.0)
    assert result["total_payout"] == 50.0


def test_hardcover_poor():
    result = process_book_buybacks([make_batch("hardcover", [make_book("poor")])], 0.0)
    assert result["total_payout"] == 6.0


def test_unrecognised_condition_is_paid_as_good():
    result = process_book_buybacks([make_batch("paperback", [make_book("fair")])], 0.0)
    assert result["total_payout"] == 8.0


def test_missing_book_fields_use_defaults():
    result = process_book_buybacks([make_batch("paperback", [{}])], 0.0)
    assert result["total_payout"] == 8.0


def test_book_with_missing_pages_is_rejected():
    batches = [make_batch("paperback", [make_book(missing=3), make_book()])]
    assert process_book_buybacks(batches, 0.0)["total_payout"] == 8.0


def test_single_missing_page_is_rejected():
    batches = [make_batch("paperback", [make_book(missing=1)])]
    assert process_book_buybacks(batches, 0.0)["status"] == "ZERO_CREDIT"


def test_counterfeit_textbook_wipes_batch_credit():
    batches = [make_batch("textbook", [make_book(), make_book(counterfeit=True), make_book()])]
    result = process_book_buybacks(batches, 0.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_counterfeit_paperback_only_that_book_is_dropped():
    batches = [make_batch("paperback", [make_book(counterfeit=True), make_book()])]
    assert process_book_buybacks(batches, 0.0)["total_payout"] == 8.0


def test_counterfeit_hardcover_only_that_book_is_dropped():
    batches = [make_batch("hardcover", [make_book(), make_book(counterfeit=True)])]
    assert process_book_buybacks(batches, 0.0)["total_payout"] == 15.0


# ---------- process_book_buybacks: payout_in_credit and final status ----------

def test_payout_in_credit_adds_bonus():
    batches = [make_batch("paperback", [make_book()], in_credit=True)]
    assert process_book_buybacks(batches, 5.0)["total_payout"] == 13.0


def test_bonus_applies_even_after_counterfeit_textbook_wipe():
    batches = [make_batch("textbook", [make_book(counterfeit=True)], in_credit=True)]
    result = process_book_buybacks(batches, 5.0)
    assert result == {"total_payout": 5.0, "status": "COMPLETED"}


def test_multiple_batches_are_summed():
    batches = [make_batch("paperback", [make_book()]), make_batch("hardcover", [make_book()])]
    assert process_book_buybacks(batches, 0.0)["total_payout"] == 23.0


def test_exactly_four_rejections_is_not_audit_rejected():
    books = [make_book(missing=1) for _ in range(4)] + [make_book()]
    result = process_book_buybacks([make_batch("paperback", books)], 0.0)
    assert result == {"total_payout": 8.0, "status": "COMPLETED"}


def test_audit_rejected_when_more_than_four_rejections():
    books = [make_book(missing=1) for _ in range(5)] + [make_book()]
    result = process_book_buybacks([make_batch("paperback", books)], 0.0)
    assert result == {"total_payout": 8.0, "status": "AUDIT_REJECTED"}


def test_audit_rejected_takes_priority_over_zero_credit():
    books = [make_book(missing=1) for _ in range(5)]
    result = process_book_buybacks([make_batch("paperback", books)], 0.0)
    assert result == {"total_payout": 0.0, "status": "AUDIT_REJECTED"}


# ---------- inspect_scanner_calibration ----------

def test_scanner_no_data():
    assert inspect_scanner_calibration([]) == "NO_DATA"


def test_scanner_recalibrate_on_two_bad_readings_in_a_row():
    assert inspect_scanner_calibration([[1, 6, 7]]) == "RECALIBRATE"


def test_scanner_calibrated_when_streak_is_broken():
    assert inspect_scanner_calibration([[6, 1, 6, 1]]) == "CALIBRATED"


def test_scanner_boundary_error_rate_of_five_is_not_a_misread():
    assert inspect_scanner_calibration([[5, 5, 5]]) == "CALIBRATED"


def test_scanner_single_bad_reading_is_not_enough():
    assert inspect_scanner_calibration([[9]]) == "CALIBRATED"


def test_scanner_empty_device_readings():
    assert inspect_scanner_calibration([[]]) == "CALIBRATED"


def test_scanner_streak_resets_between_devices():
    assert inspect_scanner_calibration([[9], [9]]) == "CALIBRATED"


def test_scanner_second_device_triggers_recalibrate():
    assert inspect_scanner_calibration([[1, 2], [8, 9]]) == "RECALIBRATE"
