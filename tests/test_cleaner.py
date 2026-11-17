from campus_help.ingestion.cleaner import clean_text


def test_clean_text_removes_layout_noise_but_preserves_policy_content():
    text = "Students must pay the fee-\nby Friday.\r\n\r\n\r\nLate fees: Rs. 500."
    assert clean_text(text) == "Students must pay the fee by Friday.\n\nLate fees: Rs. 500."


def test_clean_text_strips_outer_whitespace():
    assert clean_text("  Attendance: 75%  ") == "Attendance: 75%"
