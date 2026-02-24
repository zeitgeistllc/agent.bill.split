# Bill Splitter Application / מערכת חלוקת חשבונות דירות

A Streamlit-based application for automatically splitting household bills between two apartments based on meter readings and consumption data.

## Features

- **Automatic PDF Processing**: Extracts data from electricity, water, and city tax bills
- **OCR for Meter Reading**: Processes meter images to extract readings automatically
- **Smart Calculation Logic**:
  - City tax: 50/50 split
  - Electricity & Water: 
    - Fixed charges: 50/50 split
    - Consumption: Based on individual meter readings
- **History Tracking**: Keeps track of all calculations
- **Export Functionality**: Export results to CSV
- **Hebrew UI**: Full Hebrew interface support

## Installation

### Option 1: Local Installation

1. **Install System Dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-heb tesseract-ocr-eng
   
   # macOS
   brew install tesseract
   brew install tesseract-lang
   
   # Windows
   # Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

### Option 2: Docker

1. **Build the Docker Image**:
   ```bash
   docker build -t bill-splitter .
   ```

2. **Run the Container**:
   ```bash
   docker run -p 8501:8501 bill-splitter
   ```

3. **Access the Application**:
   Open your browser and navigate to `http://localhost:8501`

## Usage

### 1. Initial Setup
- In the sidebar, enter previous meter readings for electricity and water
- Click "שמור קריאות קודמות" (Save Previous Readings)

### 2. Upload Files
Navigate to the "העלאת חשבונות" (Upload Bills) tab:
- Upload PDF bills for electricity, water, and city tax
- Upload meter images for apartment 1 (electricity and water)
- Click "עבד קבצים" (Process Files)

### 3. Review and Edit
Navigate to the "חישוב וחלוקה" (Calculate Split) tab:
- Review extracted data
- Manually edit values if needed
- Enter current meter readings

### 4. Calculate
- Click "חשב חלוקה" (Calculate Split)
- Review the results table showing:
  - Individual bill splits
  - Total amount for each apartment
- Export results to CSV if needed

### 5. View History
Navigate to the "היסטוריה" (History) tab to view previous calculations

## File Structure

```
bill-splitter/
│
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── README.md             # Documentation
│
└── .streamlit/
    └── config.toml       # Streamlit configuration
```

## How It Works

### Bill Processing Logic

1. **City Tax (ארנונה)**:
   - Simple 50/50 split between apartments

2. **Electricity & Water**:
   - **Fixed Charges**: Split 50/50 (service fees, meter costs, etc.)
   - **Consumption Charges**: 
     - Apartment 1: Pays based on its sub-meter reading
     - Apartment 2: Pays the remainder (total - apartment 1)

### Data Extraction

The application uses:
- **pdfplumber**: For extracting text from PDF bills
- **pytesseract**: For OCR on meter images
- **Regular expressions**: For parsing amounts and consumption values

## Troubleshooting

### Common Issues

1. **OCR Not Working**:
   - Ensure Tesseract is installed correctly
   - Check that Hebrew language pack is installed
   - Try improving image quality or lighting

2. **PDF Extraction Errors**:
   - Ensure PDFs are text-based, not scanned images
   - Check PDF format matches expected patterns

3. **Calculation Errors**:
   - Verify previous meter readings are entered correctly
   - Check that consumption values are reasonable

## Configuration

Edit `.streamlit/config.toml` to customize:
- Theme colors
- Upload size limits
- Security settings

## Development

To add new features or modify the application:

1. **Add New Bill Types**:
   - Update `BillProcessor.extract_from_pdf()` with new patterns
   - Add calculation logic in `BillCalculator.calculate_split()`

2. **Improve OCR**:
   - Preprocess images in `extract_meter_reading()`
   - Add more number pattern recognition

3. **Enhance UI**:
   - Modify layout in `main()` function
   - Add new tabs or features as needed

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions, please refer to the documentation or create an issue in the project repository.