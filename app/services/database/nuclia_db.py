import json
import logging
import base64
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from nucliadb_sdk import NucliaDB

load_dotenv()

logger = logging.getLogger(__name__)


def _resolve_knowledge_box_id(sdk, kb_slug: str) -> Optional[str]:
    """
    Gets the existing Knowledge Box ID from environment variables.
    """
    kbid = os.getenv("NUCLIADB_KBID")

    if not kbid:
        logger.error(
            f"Knowledge Box ID not configured for '{kb_slug}'. "
            "Set NUCLIADB_KBID in your .env file."
        )
        return None

    return kbid.strip()


def push_to_nuclia(
    document_id: str,
    extracted_data: dict,
    file_path: Optional[str] = None
) -> bool:
    """
    Pushes extracted invoice data and an optional original file
    to the local NucliaDB.
    """

    try:
        sdk = NucliaDB(
            region="on-prem",
            url=os.getenv(
                "NUCLIADB_URL",
                "http://localhost:8080/api"
            )
        )

        kb_slug = "invoice_kb"

        kbid = _resolve_knowledge_box_id(sdk, kb_slug)

        if not kbid:
            return False

        if not isinstance(extracted_data, dict):
            logger.error("Extracted data must be a dictionary.")
            return False

        text_content = json.dumps(
            extracted_data,
            ensure_ascii=False
        )

        kwargs = {
            "kbid": kbid,
            "texts": {
                "text": {
                    "body": text_content
                }
            },
            "slug": f"doc_{document_id}",
            "title": f"Invoice {document_id}"
        }

        # Attach original invoice file
        if file_path:
            path = Path(file_path)

            if not path.is_file():
                logger.error(f"Invoice file not found: {file_path}")
                return False

            with path.open("rb") as f:
                file_bytes = f.read()

            kwargs["files"] = {
                "file": {
                    "file": {
                        "filename": path.name,
                        "payload": base64.b64encode(
                            file_bytes
                        ).decode("utf-8")
                    }
                }
            }

        # Upload resource to NucliaDB
        response = sdk.create_resource(**kwargs)

        logger.info(
            f"Successfully pushed invoice to NucliaDB: {document_id}"
        )

        return True

    except Exception:
        logger.exception(
            f"Failed to push document {document_id} to NucliaDB"
        )
        return False