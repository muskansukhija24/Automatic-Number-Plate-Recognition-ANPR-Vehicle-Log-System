# ANPR System — Architecture, UML & Design Diagrams

This document contains complete structural and behavioral diagrams for the **Automatic Number Plate Recognition (ANPR) & Vehicle Log System**, specified in Mermaid syntax.

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    subgraph InputLayer ["1. Input & Ingestion Layer"]
        A1[Single Vehicle Image] --> B[main.py CLI Interface]
        A2[Batch Directory of Images] --> B
    end

    subgraph Module1 ["2. Module 1: Plate Localization (Classical CV)"]
        B --> C1[Grayscale Normalization]
        C1 --> C2[Edge-Preserving Bilateral Filter]
        C2 --> C3[Morphological Black-Hat Transform]
        C3 --> C4[Sobel Vertical Gradient / Canny Edges]
        C4 --> C5[Rectangular Morphological Closing]
        C5 --> C6[Otsu Threshold & Contour Extraction]
        C6 --> C7{Geometric Filtering:\nAspect Ratio 1.8-7.5\nArea & Extent}
        C7 -->|Valid Quad Found| C8[4-Point Perspective Transform Deskew]
        C7 -->|No Candidate| C9[Graceful Fallback / UNREADABLE]
    end

    subgraph Module2 ["3. Module 2: OCR & Text Post-Processing"]
        C8 --> D1[Plate Crop Preprocessing & Rescaling]
        D1 --> D2[Multi-Engine OCR: EasyOCR / Tesseract / Fallback]
        D2 --> D3[Positional Character Disambiguation]
        D3 --> D4{Syntax Regex Validation\n^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$}
        D4 -->|Valid| D5[Clean Plate Number & Confidence]
        D4 -->|Invalid| D6[UNREADABLE Status]
    end

    subgraph Module3 ["4. Module 3: Persistent Storage & Audit"]
        D5 --> E1[(SQLite Database\nvehicle_logs)]
        D6 --> E1
        E1 --> E2[Watchlist / Blacklist Check]
        E1 --> E3[Rotating File Logger\nlogs/app.log]
    end

    subgraph Module4 ["5. Module 4: CLI Presentation & Analytics"]
        E2 --> F1[Rich Terminal Table Output]
        E1 --> F2[Summary Statistics Dashboard]
        E1 --> F3[CSV Report Exporter]
    end
```

---

## 2. End-to-End Workflow Diagram

```mermaid
flowchart LR
    Start([User / Operator]) --> Mode{Select Subcommand}
    
    Mode -->|scan| S1[Provide --image path]
    S1 --> S2[Classical CV Localization]
    S2 --> S3[OCR & Positional Cleaning]
    S3 --> S4[Check Blacklist Status]
    S4 --> S5[Log to SQLite & app.log]
    S5 --> End1([Display Result Card])

    Mode -->|batch-scan| B1[Provide --dir path]
    B1 --> B2[Iterate Directory Files]
    B2 --> S2
    B2 --> End2([Display Batch Summary & CSV])

    Mode -->|list| L1[Filter by Date / Limit]
    L1 --> L2[Query SQLite vehicle_logs]
    L2 --> End3([Render Audit Table])

    Mode -->|search| SE1[Input Plate Query]
    SE1 --> SE2[Execute SQL LIKE query]
    SE2 --> End4([Display Matched Records])

    Mode -->|flag| FL1[Specify Plate & Flag/Unflag]
    FL1 --> FL2[Update Watchlist in SQLite]
    FL2 --> End5([Confirmation Message])

    Mode -->|stats| ST1[Compute Aggregates]
    ST1 --> End6([Dashboard Summary Metrics])

    Mode -->|export| EX1[Specify Output Filepath]
    EX1 --> EX2[Dump Table to CSV]
    EX2 --> End7([File Saved Notification])
```

---

## 3. Use Case Diagram

```mermaid
flowchart TD
    Actor["👤 Operator / Security Guard"]

    subgraph ANPR_System ["ANPR & Vehicle Log System (Boundaries)"]
        UC1(["Scan Single Vehicle Image (UC-1)"])
        UC2(["Batch Scan Image Directory (UC-2)"])
        UC3(["List Vehicle Logs by Date (UC-3)"])
        UC4(["Search Log by Plate Number (UC-4)"])
        UC5(["Flag / Blacklist Vehicle (UC-5)"])
        UC6(["View Dashboard Metrics (UC-6)"])
        UC7(["Export Audit Trail to CSV (UC-7)"])
        UC8(["Automatic Blacklist Alerting (UC-8)"])
    end

    Actor --> UC1
    Actor --> UC2
    Actor --> UC3
    Actor --> UC4
    Actor --> UC5
    Actor --> UC6
    Actor --> UC7

    UC1 -.->|<<include>>| UC8
    UC2 -.->|<<include>>| UC8
```

---

## 4. Class / Component Diagram

```mermaid
classDiagram
    class PlateDetector {
        +float min_aspect_ratio
        +float max_aspect_ratio
        +float min_area_ratio
        +float max_area_ratio
        +int canonical_width
        +detect(image_input) PlateDetectionResult
        -_detect_via_morphology()
        -_detect_via_adaptive_threshold()
        -_find_best_contour()
        -_finalize_candidate()
    }

    class PlateDetectionResult {
        +bool is_detected
        +ndarray plate_crop
        +tuple bbox
        +ndarray polygon
        +float aspect_ratio
        +float confidence
        +str message
    }

    class OCRReader {
        +str preferred_engine
        +bool gpu
        +dict ALPHA_CONFUSIONS
        +dict NUMERIC_CONFUSIONS
        +Pattern STRICT_PLATE_REGEX
        +Pattern GENERIC_PLATE_REGEX
        +preprocess_plate(plate_crop) list
        +read_plate(plate_crop) OCRResult
        +clean_plate_text(text) str
        -_run_easyocr()
        -_run_tesseract()
        -_run_cv_fallback()
        -_get_templates()
    }

    class OCRResult {
        +str raw_text
        +str clean_text
        +float confidence
        +bool is_valid
        +str status
        +str engine_used
    }

    class DBManager {
        +str db_path
        +_init_db()
        +is_plate_flagged(plate_number) bool
        +insert_log(plate, conf, path, flagged, status) int
        +get_logs(date_str, limit, offset) list
        +search_by_plate(query, exact) list
        +set_flag(plate, flagged) int
        +get_summary_stats() dict
        +export_to_csv(output_filepath) str
    }

    class Utils {
        +load_image(image_input) ndarray
        +save_image(image, output_path) str
        +resize_image(image, width, height) tuple
        +order_points(pts) ndarray
        +four_point_transform(image, pts) ndarray
        +enhance_plate_contrast(gray_plate) ndarray
    }

    class CLI_Dashboard {
        +handle_scan()
        +handle_batch_scan()
        +handle_list()
        +handle_search()
        +handle_flag()
        +handle_stats()
        +handle_export()
        +main()
    }

    PlateDetector ..> PlateDetectionResult : creates
    PlateDetector ..> Utils : uses
    OCRReader ..> OCRResult : creates
    OCRReader ..> Utils : uses
    CLI_Dashboard --> PlateDetector : invokes
    CLI_Dashboard --> OCRReader : invokes
    CLI_Dashboard --> DBManager : persists
```

---

## 5. Sequence Diagram: Single Image Scan Execution

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Operator / User
    participant CLI as main.py (CLI)
    participant Detector as PlateDetector
    participant Utils as utils.py
    participant OCR as OCRReader
    participant DB as DBManager
    participant Logger as RotatingFileLogger

    Operator->>CLI: python main.py scan --image car.jpg
    CLI->>Logger: log scan requested
    CLI->>Detector: detect("car.jpg")
    Detector->>Utils: load_image("car.jpg")
    Utils-->>Detector: BGR ndarray
    Detector->>Detector: bilateralFilter + blackHat + morphology
    Detector->>Utils: four_point_transform(image, pts)
    Utils-->>Detector: deskewed plate_crop
    Detector-->>CLI: PlateDetectionResult(is_detected=True, plate_crop)

    CLI->>OCR: read_plate(plate_crop)
    OCR->>OCR: preprocess_plate() [CLAHE, Otsu]
    OCR->>OCR: run_engine() [EasyOCR / Tesseract / Fallback]
    OCR->>OCR: clean_plate_text() [positional disambiguation]
    OCR->>OCR: validate regex & score
    OCR-->>CLI: OCRResult(clean_text="DL01AB1234", conf=0.95, status="DETECTED")

    CLI->>DB: is_plate_flagged("DL01AB1234")
    DB-->>CLI: is_flagged = False
    CLI->>DB: insert_log(plate, conf, path, flagged=0, status)
    DB-->>CLI: log_id = 42
    CLI->>Logger: log insertion & metrics
    CLI-->>Operator: Display formatted Result Card & CPU execution time
```

---

## 6. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    VEHICLE_LOGS {
        INTEGER id PK "AUTOINCREMENT"
        TEXT plate_number "NOT NULL, INDEXED"
        DATETIME timestamp "DEFAULT CURRENT_TIMESTAMP, INDEXED"
        REAL confidence "NOT NULL (0.00 to 1.00)"
        TEXT image_path "NOT NULL"
        INTEGER flagged "DEFAULT 0 (0=Clean, 1=Blacklisted)"
        TEXT status "DEFAULT 'DETECTED'"
    }
```

### Database Schema DDL Design
```sql
CREATE TABLE IF NOT EXISTS vehicle_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
    confidence REAL NOT NULL,
    image_path TEXT NOT NULL,
    flagged INTEGER DEFAULT 0,
    status TEXT DEFAULT 'DETECTED'
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_logs_plate ON vehicle_logs(plate_number);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON vehicle_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_flagged ON vehicle_logs(flagged);
```
