import os
import requests
import time
import mimetypes
import csv
from datetime import datetime

URL = "http://127.0.0.1:8000/api/v1/invoices/upload"
FOLDER_PATH = "test_bills"

if not os.path.exists(FOLDER_PATH):
    print(f"Error: '{FOLDER_PATH}' folder nahi mila.")
    exit()

files = os.listdir(FOLDER_PATH)
print(f"Total {len(files)} bills mil gaye. Upload shuru kar rahe hain...\n")

success_count = 0
fail_count = 0

# CSV File banane ka setup
csv_filename = f"upload_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
print(f"Results is file mein save honge: {csv_filename}\n")

with open(csv_filename, mode='w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file)
    # CSV ke Headers
    writer.writerow(["Filename", "Document_ID", "Status", "Error_Message"])

    for index, filename in enumerate(files, 1):
        file_path = os.path.join(FOLDER_PATH, filename)
        
        if not os.path.isfile(file_path):
            continue
            
        try:
            mime_type, _ = mimetypes.guess_type(filename)
            
            if mime_type is None:
                if filename.lower().endswith('.png'): mime_type = 'image/png'
                elif filename.lower().endswith(('.jpg', '.jpeg')): mime_type = 'image/jpeg'
                elif filename.lower().endswith('.pdf'): mime_type = 'application/pdf'
                else: mime_type = 'application/octet-stream'

            print(f"[{index}/{len(files)}] Uploading: {filename}...")
            
            with open(file_path, "rb") as f:
                files_payload = {"file": (filename, f, mime_type)}
                response = requests.post(URL, files=files_payload)
                
            if response.status_code == 200:
                doc_id = response.json().get("document_id")
                print(f"✅ Success! ID: {doc_id}\n")
                success_count += 1
                # CSV mein Success likho
                writer.writerow([filename, doc_id, "SUCCESS", ""])
            else:
                print(f"❌ Failed! Server Response: {response.text}\n")
                fail_count += 1
                # CSV mein Fail likho
                writer.writerow([filename, "N/A", "FAILED", response.text])
                
        except Exception as e:
            print(f"❌ Error uploading {filename}: {e}\n")
            fail_count += 1
            writer.writerow([filename, "N/A", "ERROR", str(e)])
            
        time.sleep(2)

print("\n--- UPLOAD COMPLETE ---")
print(f"Successfully Queued: {success_count}")
print(f"Failed to Queue: {fail_count}")
print(f"📄 Saari details yahan save ho gayi hain: {csv_filename}")