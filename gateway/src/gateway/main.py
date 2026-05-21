from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import fal_client
import os
import asyncio
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

# --- Pydantic Schemas ---

class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., description="Image generation prompt", min_length=1)
    model: str = Field(default="fal-ai/flux/schnell", description="Fal model endpoint")
    image_size: str = Field(default="landscape_4_3", description="Image aspect ratio")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    num_images: int = Field(default=1, ge=1, le=4, description="Number of images to generate")
    safety_tolerance: str = Field(default="2", description="Safety filter level")

class GenerateVideoRequest(BaseModel):
    prompt: str = Field(..., description="Video generation prompt", min_length=1)
    model: str = Field(default="fal-ai/kling-video/v1/standard/text-to-video", description="Fal video model endpoint")
    duration: Literal["5", "10"] = Field(default="5", description="Video duration in seconds")
    aspect_ratio: str = Field(default="16:9", description="Video aspect ratio")

class GenerateAudioRequest(BaseModel):
    prompt: str = Field(..., description="Audio/music generation prompt", min_length=1)
    model: str = Field(default="fal-ai/stable-audio", description="Fal audio model endpoint")
    duration: int = Field(default=10, ge=1, le=45, description="Audio duration in seconds")

class GenerateResponse(BaseModel):
    status: str
    model: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    request_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"

# --- App Factory ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    api_key = os.environ.get("FAL_KEY")
    if not api_key:
        logger.warning("FAL_KEY not set — fal.ai calls will fail!")
    else:
        logger.info("FAL_KEY loaded (masked)")
    yield
    # Shutdown
    logger.info("Gateway shutting down")

app = FastAPI(
    title="Xcity Fal Media Gateway",
    description="Unified API for generating images, videos, and audio via fal.ai",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Helpers ---

def _get_client():
    """Sync fal_client with FAL_KEY from env."""
    api_key = os.environ.get("FAL_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FAL_KEY not configured")
    return fal_client.SyncClient(key=api_key)

# --- Routes ---

@app.get("/", response_model=HealthResponse)
def root():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.post("/generate/image", response_model=GenerateResponse)
def generate_image(req: GenerateImageRequest):
    client = _get_client()
    try:
        arguments = {
            "prompt": req.prompt,
            "image_size": req.image_size,
            "num_images": req.num_images,
            "safety_tolerance": req.safety_tolerance,
        }
        if req.seed is not None:
            arguments["seed"] = req.seed

        result = client.subscribe(
            req.model,
            arguments=arguments,
        )
        return {
            "status": "success",
            "model": req.model,
            "result": result,
        }
    except Exception as exc:
        logger.error(f"Image generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"fal.ai error: {exc}")

@app.post("/generate/video", response_model=GenerateResponse)
def generate_video(req: GenerateVideoRequest):
    client = _get_client()
    try:
        arguments = {
            "prompt": req.prompt,
            "duration": req.duration,
            "aspect_ratio": req.aspect_ratio,
        }
        result = client.subscribe(
            req.model,
            arguments=arguments,
        )
        return {
            "status": "success",
            "model": req.model,
            "result": result,
        }
    except Exception as exc:
        logger.error(f"Video generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"fal.ai error: {exc}")

@app.post("/generate/audio", response_model=GenerateResponse)
def generate_audio(req: GenerateAudioRequest):
    client = _get_client()
    try:
        arguments = {
            "prompt": req.prompt,
            "seconds_total": req.duration,
        }
        result = client.subscribe(
            req.model,
            arguments=arguments,
        )
        return {
            "status": "success",
            "model": req.model,
            "result": result,
        }
    except Exception as exc:
        logger.error(f"Audio generation failed: {exc}")
        raise HTTPException(status_code=502, detail=f"fal.ai error: {exc}")

@app.post("/generate/any")
def generate_any(
    model: str,
    arguments: dict[str, Any],
):
    """Generic endpoint — pass any fal.ai model ID and arguments directly."""
    client = _get_client()
    try:
        result = client.subscribe(model, arguments=arguments)
        return {
            "status": "success",
            "model": model,
            "result": result,
        }
    except Exception as exc:
        logger.error(f"Generation failed for {model}: {exc}")
        raise HTTPException(status_code=502, detail=f"fal.ai error: {exc}")

# Error handler
@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": str(exc)},
    )
