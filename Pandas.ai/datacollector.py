import pandasai as pai
import pandas as pd
import os
import glob
from bs4 import BeautifulSoup
import re
from datetime import datetime

# Set API key
pai.api_key.set("YOUR_API_KEY")

def parse_html_report(html_file_path):
    """Parse HTML report and extract scan data."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Extract scan information
        scan_info = {}
        scan_info_section = soup.find('div', class_='scan-info')
        if scan_info_section:
            for p in scan_info_section.find_all('p'):
                text = p.get_text()
                if ':' in text:
                    key, value = text.split(':', 1)
                    scan_info[key.strip()] = value.strip()
        
        # Extract summary statistics
        summary = {}
        summary_cards = soup.find_all('div', class_='summary-card')
        for card in summary_cards:
            title = card.find('h3').get_text().strip()
            number = card.find('div', class_='number').get_text().strip()
            summary[title] = number
        
        # Extract file details
        files_data = []
        file_cards = soup.find_all('div', class_='file-card')
        for card in file_cards:
            file_data = {}
            
            # File path
            path_elem = card.find('div', class_='file-path')
            if path_elem:
                file_data['file_path'] = path_elem.get_text().strip().split(' ', 1)[1]  # Remove emoji
            
            # File info
            info_elems = card.find_all('span')
            for info in info_elems:
                text = info.get_text()
                if ':' in text:
                    key, value = text.split(':', 1)
                    file_data[key.strip()] = value.strip()
            
            # PII entities
            pii_entities = []
            pii_section = card.find('div', class_='pii-entities')
            if pii_section:
                pii_elems = pii_section.find_all('div', class_='pii-entity')
                for pii in pii_elems:
                    pii_text = pii.get_text()
                    if ':' in pii_text:
                        label, text = pii_text.split(':', 1)
                        pii_entities.append({
                            'label': label.strip(),
                            'text': text.strip()
                        })
            
            file_data['pii_entities'] = pii_entities
            file_data['pii_count'] = len(pii_entities)
            file_data['has_pii'] = len(pii_entities) > 0
            
            files_data.append(file_data)
        
        return {
            'scan_info': scan_info,
            'summary': summary,
            'files': files_data,
            'report_file': os.path.basename(html_file_path)
        }
        
    except Exception as e:
        print(f"Error parsing HTML report {html_file_path}: {e}")
        return None

def collect_data_from_reports():
    """Collect data from all HTML reports in the reports directory."""
    reports_dir = os.path.join('..', 'reports')
    
    if not os.path.exists(reports_dir):
        print(f"Reports directory not found: {reports_dir}")
        return None
    
    # Find all HTML reports
    html_files = glob.glob(os.path.join(reports_dir, '*.html'))
    
    if not html_files:
        print("No HTML reports found")
        return None
    
    all_data = []
    
    for html_file in html_files:
        print(f"Processing report: {os.path.basename(html_file)}")
        report_data = parse_html_report(html_file)
        if report_data:
            all_data.append(report_data)
    
    return all_data

def create_dataframe_from_reports(reports_data):
    """Convert reports data to a pandas DataFrame."""
    if not reports_data:
        return pd.DataFrame()
    
    # Flatten the data for DataFrame creation
    rows = []
    
    for report in reports_data:
        scan_info = report['scan_info']
        summary = report['summary']
        
        for file_data in report['files']:
            row = {
                'report_file': report['report_file'],
                'scan_type': scan_info.get('Scan Type', 'Unknown'),
                'scan_path': scan_info.get('Scan Path', 'Unknown'),
                'scan_date': scan_info.get('Report Generated', 'Unknown'),
                'file_path': file_data.get('file_path', 'Unknown'),
                'file_size': file_data.get('Size', '0'),
                'file_modified': file_data.get('Modified', 'Unknown'),
                'pii_count': file_data.get('pii_count', 0),
                'has_pii': file_data.get('has_pii', False),
                'pii_entities': str(file_data.get('pii_entities', [])),
                'total_files': summary.get('Total Files', '0'),
                'files_with_pii': summary.get('Files with PII', '0'),
                'total_pii_entities': summary.get('Total PII Entities', '0'),
                'risk_level': summary.get('Risk Level', 'Unknown')
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

# Main execution
if __name__ == "__main__":
    print("Collecting data from HTML reports...")
    
    # Collect data from all reports
    reports_data = collect_data_from_reports()
    
    if not reports_data:
        print("No data collected. Exiting.")
        exit(1)
    
    # Convert to DataFrame
    pandas_df = create_dataframe_from_reports(reports_data)
    
    if pandas_df.empty:
        print("No data to process. Exiting.")
        exit(1)
    
    print(f"Collected data for {len(pandas_df)} file scans from {len(reports_data)} reports")
    
    # Convert pandas DataFrame to PandaAI DataFrame
    df = pai.DataFrame(pandas_df)
    
    # Save your dataset configuration
    dataset = pai.create(
        path="pai-personal-6a9b7/vbr-pii-scanner", 
        df=df,  # Pass the DataFrame here
        description="PII Scanner for Veeam - HTML Report Data"
    )
    
    # Push your dataset to PandaBI
    dataset.push()
    
    print("Data successfully pushed to PandaAI!")