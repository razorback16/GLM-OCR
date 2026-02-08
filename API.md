# GLM-OCR REST API

GLM-OCR exposes a REST API via its built-in Flask server (`python -m glmocr.server`).

## Endpoints

### `POST /glmocr/parse`

Parse one or more images/PDFs and return structured OCR results.

**Request**

```
Content-Type: application/json
```

```json
{
  "images": [
    "https://example.com/page.png",
    "file:///path/to/document.pdf",
    "data:image/png;base64,iVBORw0KG..."
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | `string` or `string[]` | Yes | Image source(s). Supports HTTP/HTTPS URLs, `file://` URIs, and `data:` URIs. |

**Response (200)**

```json
{
  "json_result": [
    [
      {
        "index": 0,
        "label": "text",
        "native_label": "content",
        "content": "Recognized text...",
        "bbox_2d": [100, 200, 500, 400]
      },
      {
        "index": 1,
        "label": "table",
        "native_label": "table",
        "content": "| col1 | col2 |\n|------|------|\n| a | b |",
        "bbox_2d": [50, 450, 950, 800]
      }
    ]
  ],
  "markdown_result": "Recognized text...\n\n| col1 | col2 |\n|------|------|\n| a | b |"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `json_result` | `array` | Nested array: pages → regions. Each region has `index`, `label`, `content`, and `bbox_2d`. |
| `markdown_result` | `string` | Markdown-formatted OCR output. |

**Region labels:** `text`, `table`, `formula`, `image`

**Coordinate system:** `bbox_2d` values are normalized to a 0–1000 scale (`[x1, y1, x2, y2]`). `null` when layout detection is disabled.

---

### `GET /health`

Health check.

**Response (200)**

```json
{
  "status": "ok"
}
```

---

## Error Responses

All errors return a JSON body with an `error` field.

| Status | Condition | Example |
|--------|-----------|---------|
| 400 | Missing or invalid `Content-Type` | `{"error": "Invalid Content-Type. Expected 'application/json'."}` |
| 400 | Malformed JSON | `{"error": "Invalid JSON payload"}` |
| 400 | Empty `images` | `{"error": "No images provided"}` |
| 500 | Internal processing error | `{"error": "Parse error: ..."}` |

---

## Examples

### Parse a local file

```bash
curl -X POST http://localhost:5002/glmocr/parse \
  -H "Content-Type: application/json" \
  -d '{"images": ["file:///path/to/image.png"]}'
```

### Parse a URL

```bash
curl -X POST http://localhost:5002/glmocr/parse \
  -H "Content-Type: application/json" \
  -d '{"images": ["https://example.com/document.png"]}'
```

### Parse multiple images

```bash
curl -X POST http://localhost:5002/glmocr/parse \
  -H "Content-Type: application/json" \
  -d '{"images": ["file:///tmp/page1.png", "file:///tmp/page2.png"]}'
```

### Health check

```bash
curl http://localhost:5002/health
```

---

## Docker Compose Deployment

The included `docker-compose.yml` runs vLLM (serving the GLM-OCR model) and the GLM-OCR Flask server together, both with GPU access.

### Prerequisites

- NVIDIA GPU with driver installed
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- Docker with Compose v2

### Start

```bash
# Optional: set HuggingFace token for gated models
export HUGGING_FACE_HUB_TOKEN=hf_...

docker compose up --build
```

vLLM downloads the model on first start (this takes a while). The GLM-OCR server waits for vLLM to become healthy before starting.

### Verify

```bash
# Health check
curl http://localhost:5002/health

# Parse an image
curl -X POST http://localhost:5002/glmocr/parse \
  -H "Content-Type: application/json" \
  -d '{"images": ["file:///path/to/test.png"]}'
```

### Configuration

The GLM-OCR server mounts `glmocr/config.yaml` and overrides `api_host` to `vllm` (Docker DNS) via the `GLMOCR_OCR_API_HOST` environment variable. Edit `glmocr/config.yaml` to change pipeline settings (layout detection, thresholds, etc.).

### Ports

| Service | Port | Description |
|---------|------|-------------|
| vLLM | 8099 | OpenAI-compatible API (model serving) |
| GLM-OCR | 5002 | REST API (`/glmocr/parse`, `/health`) |
