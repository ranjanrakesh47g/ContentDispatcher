import os
import sys
from pathlib import Path

import uvicorn

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    sys.path.insert(0, str(root))
    uvicorn.run(
        "src.api.app:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
