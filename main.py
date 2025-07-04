from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import re

app = FastAPI(
    title="Asset Scanner API",
    description="Extrahiert geladene Bildressourcen aus einer Website wie im Chrome Sources-Tab",
    version="1.0.0"
)

# CORS aktivieren für alle Domains (Frontend z. B. Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Alternativ: ["https://deine-vercel-app.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AssetScanResponse(BaseModel):
    url: str
    images: List[str]

@app.get("/analyze-assets", response_model=AssetScanResponse)
def analyze_assets(
    url: str = Query(...),
    enable_js: bool = Query(True)
):
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise HTTPException(status_code=400, detail="Ungültige URL")

    image_urls = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                java_script_enabled=enable_js,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.set_default_timeout(30000)

            def handle_response(response):
                try:
                    url = response.url
                    if re.search(r"\.(jpg|jpeg|png|svg|gif|webp|bmp)(\?.*)?$", url, re.IGNORECASE):
                        image_urls.add(url)
                except:
                    pass

            page.on("response", handle_response)
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(1500)
            browser.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Asset-Scan: {str(e)}")

    return AssetScanResponse(
        url=url,
        images=list(image_urls)
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "asset-scanner-api"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
