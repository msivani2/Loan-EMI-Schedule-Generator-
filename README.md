# Loan-EMI-Schedule-Generator-
# Loan EMI Schedule Generator

A web-based **Loan EMI Schedule Generator** designed for NBFC and retail lending use cases. The application allows users to upload loan master CSV files, select individual borrowers, view reducing-balance EMI schedules, and export borrower-wise repayment schedules as PDFs.

## 📌 Project Overview

The system is designed to generate accurate EMI schedules using **reducing-balance calculations**. It supports loan servicing scenarios such as monthly EMIs, floating-rate changes, prepayments, and loan closures.

The project focuses on:

* Accurate EMI calculations
* Borrower-wise repayment schedules
* CSV-based loan data processing
* Floating-rate reset handling
* PDF schedule generation
* Auditable and reproducible calculations

## ✨ Features

* Upload Loan Master CSV
* Process multiple loan records
* Select a borrower from the loan list
* Display monthly EMI schedules
* Calculate:

  * Opening Balance
  * EMI
  * Interest
  * Principal
  * Closing Balance
* Export borrower-wise PDF schedules
* Support reducing-balance amortisation
* Support floating-rate resets and re-amortisation
* Handle rounding and residual amounts
* Support prepayments and partial closures
* Audit-friendly calculation workflow

## 🖥️ User Interface

The HTML interface provides:

1. **CSV Upload**

   * Upload a `.csv` loan master file.
   * Click **Process CSV** to submit the data.

2. **Borrower Selection**

   * Select a loan from the available borrower list.

3. **EMI Schedule**

   * View the repayment schedule month by month.

4. **PDF Export**

   * Export the selected borrower's repayment schedule as a PDF.

The interface uses **Tailwind CSS** for styling.

## 📊 EMI Schedule

The schedule displays the following information:

| Column          | Description                               |
| --------------- | ----------------------------------------- |
| Month           | Payment period                            |
| Opening Balance | Outstanding loan balance at the beginning |
| EMI             | Monthly instalment                        |
| Interest        | Interest component of EMI                 |
| Principal       | Principal component of EMI                |
| Closing Balance | Remaining balance after payment           |

These fields are implemented directly in the project interface.

## 🧮 EMI Calculation

The project uses the reducing-balance EMI formula:

```text
EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
```

Where:

* `P` = Principal loan amount
* `r` = Periodic interest rate
* `n` = Number of payment periods

The outstanding principal is recalculated for each payment period.

## 📂 Input Data

The application is designed to work with a **Loan Master CSV** containing information such as:

* Borrower ID
* Principal amount
* Tenure
* Start date
* Annual interest rate
* Interest type
* EMI frequency
* Prepayment events
* Rounding policy

## 🔄 Workflow

```text
Upload Loan Master CSV
          ↓
Schema Validation
          ↓
Rate Processing
          ↓
EMI / Amortisation Calculation
          ↓
Rounding & Residual Handling
          ↓
Generate Repayment Schedule
          ↓
Export Borrower PDF
```

The proposed workflow follows CSV ingestion, validation, rate processing, amortisation, rounding, and borrower-wise PDF generation.

## 🏗️ Project Modules

The planned system consists of the following modules:

1. CSV Parser & Validator
2. Rate Engine & Reset Handler
3. Amortisation Calculator
4. Rounding & Residual Manager
5. PDF Exporter & Batch Scheduler
6. Test Harness & Audit Logger

## 💻 Technologies

* **HTML**
* **JavaScript**
* **Tailwind CSS**
* **Python** (backend/service)
* **Pandas**
* **ReportLab**
* **APScheduler**
* **CSV**

The project overview specifies a Python service with libraries such as pandas, ReportLab, and APScheduler.

## 🔌 Backend API Endpoints

The frontend communicates with backend endpoints for:

```text
POST /upload-csv
GET  /loans
GET  /loan/{loanId}/schedule
GET  /loan/{loanId}/pdf
```

The HTML frontend uses these endpoints to upload CSV data, retrieve loans, display schedules, and open borrower PDFs.

## 📁 Suggested Repository Structure

```text
Loan-EMI-Schedule-Generator/
│
├── README.md
├── python.html
├── requirements.txt
│
├── backend/
│   ├── main.py
│   ├── loan_calculator.py
│   ├── csv_parser.py
│   ├── pdf_exporter.py
│   └── audit_logger.py
│
├── data/
│   └── loan_master.csv
│
├── output/
│   └── borrower_pdfs/
│
└── tests/
    ├── test_emi.py
    └── test_schedule.py
```

## 🧪 Testing

Testing can include:

* EMI calculation tests
* Amortisation calculation tests
* CSV validation tests
* Floating-rate reset tests
* Prepayment tests
* Rounding and residual tests
* CSV-to-PDF integration tests
* Loan closure reconciliation tests

The project specifically identifies unit, integration, and reconciliation testing as part of its testing approach.

## 🎯 Future Enhancements

* Add a complete Python/FastAPI backend
* Add database integration
* Add authentication and user roles
* Add dashboard with loan statistics
* Add downloadable CSV schedules
* Add advanced floating-rate configuration
* Add automated batch processing
* Add comprehensive audit logs
* Add automated unit and integration testing

## 👥 Team

* **2500520001** — TALABATTULA SRI KRISHNA VARDHAN
* **2500520002** — MAMIDI SIVANI
* **2500520003** — CHIKKAM RAMA SURYA

## 📜 License

This project is developed for academic and educational purposes.

---

### Project Title

**Loan EMI Schedule Generator**

A compact solution for generating accurate, auditable and borrower-wise loan repayment schedules.
