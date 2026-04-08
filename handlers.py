import json


def extract_pdf_text(context, payload):
    input_text = payload.get("input_text", "")

    extracted_text = input_text
    doc_count = 1

    if "pdf" in input_text.lower() or "document" in input_text.lower():
        extracted_text = input_text + "\n\n[PDF content would be extracted here]"
        doc_count = 1

    return {
        "extracted_text": extracted_text,
        "doc_count": doc_count,
        "text_length": len(extracted_text),
    }


def validate_documents(context, payload):
    expected = payload.get("expected_docs", [])
    provided = payload.get("provided_docs", [])
    missing = [doc for doc in expected if doc not in provided]

    return {
        "is_valid": len(missing) == 0,
        "missing_docs": missing,
        "validation_message": "All documents present"
        if len(missing) == 0
        else f"Missing: {', '.join(missing)}",
    }


def get_seller_name(context, payload):
    company_name = str(payload.get("company_name", "")).strip().lower()
    stakeholder_map = {
        "google": "Sundar Pichai",
        "microsoft": "Satya Nadella",
        "apple": "Tim Cook",
        "amazon": "Andy Jassy",
    }
    return stakeholder_map.get(company_name, "unknown")
