from app.services.database.nuclia_db import push_to_nuclia

def main():
    sample_data = {
        "invoice_no": "INV-2026-99",
        "date": "18 Nov 2026",
        "vendor": "Tech Store",
        "total": 1500
    }

    success = push_to_nuclia(document_id="test_001", extracted_data=sample_data)
    
    if success:
        print("Data insertion successful.")
    else:
        print("Data insertion failed. Check logs.")

if __name__ == "__main__":
    main()