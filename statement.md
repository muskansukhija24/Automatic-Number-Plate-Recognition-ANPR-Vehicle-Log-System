# Automatic Number Plate Recognition (ANPR) & Vehicle Log System

## 1. Problem Statement

Automated vehicle identification is a critical infrastructure requirement for modern intelligent transportation systems (ITS), automated toll collection plazas, secure parking management, and law enforcement surveillance. Traditional manual logging methods are slow, error-prone, labor-intensive, and incapable of operating under high-throughput traffic conditions. 

This project addresses these challenges by developing a robust, lightweight, end-to-end **Automatic Number Plate Recognition (ANPR) & Vehicle Log System** built using Python and classical computer vision. The system localizes vehicle license plates from camera imagery, rectifies perspective skew, extracts and cleans alphanumeric characters, validates license plate syntax, monitors vehicles against an active blacklist/watchlist, and logs all audit events to a persistent SQLite database with rotating file logs.

---

## 2. Project Scope

### In Scope
- **Image Input Ingestion:** Processing individual vehicle frames, camera stills, and batch directories in standard formats (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`).
- **Classical CV Plate Localization:** Dual-pipeline edge and morphological localization (grayscale conversion, edge-preserving bilateral filtering, morphological black-hat transforms, vertical Sobel gradients, rectangular morphological closing, contour analysis, aspect ratio filtering, and extent validation).
- **Perspective Homography Rectification:** 4-point perspective transformation to deskew tilted or angled license plates into planar, upright rectangular crops.
- **Optical Character Recognition (OCR):** Alphanumeric text extraction with adaptive thresholding, multi-engine support (EasyOCR, PyTesseract, and standalone CV contour character template matcher), positional letter/digit disambiguation, and regex validation.
- **Audit Logging & Querying:** SQLite relational storage (`vehicle_logs`), supporting date filtering, partial and exact plate searching, record flagging/blacklisting, and CSV export.
- **Unified Command-Line Dashboard:** Rich CLI interface supporting `scan`, `batch-scan`, `list`, `search`, `flag`, `stats`, and `export` subcommands.
- **Graceful Error Handling:** Reliable degradation on blurry, noisy, or plate-free imagery without unhandled exceptions.

### Out of Scope
- Direct physical hardware interfacing with automated toll gate barriers or RFID readers.
- Real-time video streaming across multi-camera RTSP networks (system is designed for single-frame and batch-image processing).
- Multi-lane multi-vehicle simultaneous tracking.

---

## 3. Target Users

1. **Security & Parking Facility Operators:** Automated logging of ingress and egress vehicles in gated commercial and residential complexes.
2. **Toll Plaza Authorities:** Automated, contactless audit logging of vehicle registrations for toll reconciliation.
3. **Law Enforcement & Traffic Police:** Rapid real-time screening of suspect or blacklisted vehicles against hotlists.
4. **Fleet & Logistics Managers:** Depot gate monitoring to track vehicle turnaround and operational schedules.

---

## 4. High-Level Features

- **Classical Computer Vision Localization:** Zero deep-learning dependency for plate localization; relies entirely on explainable, deterministic OpenCV transforms.
- **Perspective Deskewing:** Employs 4-point homography transformations to rectify angled vehicle license plates.
- **Multi-Engine OCR with Smart Disambiguation:** Seamlessly interfaces with EasyOCR or PyTesseract, complemented by positional letter-to-digit and digit-to-letter correction algorithms (e.g. correcting `0` vs `O`, `1` vs `I`, `8` vs `B`).
- **Real-Time Blacklist / Watchlist Alerting:** Immediate visual alerting when a scanned plate matches a flagged vehicle in the database.
- **Dual-Layer Persistent Audit Trail:** Every scan writes to both a structured SQLite database (`data/vehicle_logs.db`) and a rotating file log (`logs/app.log`).
- **Rich Interactive CLI Dashboard:** Formatted terminal tables, execution benchmarks, and summary statistics.
- **Instant CSV Export:** Frictionless one-command export of audit records for external reporting.
