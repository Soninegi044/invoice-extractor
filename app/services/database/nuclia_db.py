import json
import logging
from nucliadb_sdk import NucliaDB

logger = logging.getLogger(__name__)

def push_to_nuclia(document_id: str, extracted_data: dict):
    try:
        # 1. SDK Initialize (Warning fix: region="on-prem")
        sdk = NucliaDB(region="on-prem", url="http://localhost:8080/api")
        
        text_content = json.dumps(extracted_data, ensure_ascii=False)
        kb_slug = "invoice_kb"
        
        # 2. Knowledge Box (Database) check karein ya naya banayein
        try:
            kb = sdk.get_knowledge_box(slug=kb_slug)
        except Exception:
            kb = sdk.create_knowledge_box(slug=kb_slug)
            
        kbid = kb.uuid
        if not kbid:
            # Agar phir bhi ID na mile, toh list se pehla utha lein
            kbs = sdk.list_knowledge_boxes()
            if kbs:
                kbid = kbs[0].uuid
            else:
                raise ValueError("Knowledge Box ID nahi mili!")

        # 3. Data push karein
        sdk.create_resource(
            kbid=kbid,
            texts={"text": {"body": text_content}},
            slug=document_id
        )
        
        logger.info(f"Successfully pushed document {document_id} to Local NuDB (KB: {kbid}).")
        return True
    except Exception as e:
        logger.error(f"Failed to push to NuDB: {e}")
        return False