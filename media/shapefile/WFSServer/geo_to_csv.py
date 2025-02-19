import json
import csv
from typing import Dict, List, Any

def convert_geojson_to_csv(input_file: str, output_file: str, selected_features: List[str]):
    try:
        # Read GeoJSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        # Extract features
        if isinstance(geojson_data, dict):
            features = geojson_data.get('features', [])
        elif isinstance(geojson_data, list):
            features = geojson_data
        else:
            raise ValueError("Invalid GeoJSON format")
            
        # Prepare CSV data
        csv_data = []
        for feature in features:
            properties = feature.get('properties', {})
            row = {key: properties.get(key, '') for key in selected_features}
            csv_data.append(row)
            
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=selected_features)
            writer.writeheader()
            writer.writerows(csv_data)
            
        print(f"Successfully converted {len(features)} features to CSV: {output_file}")
        
    except Exception as e:
        print(f"Error converting GeoJSON to CSV: {str(e)}")
        raise

# Example usage:
if __name__ == '__main__':
    # Specify which features you want to extract as a list
    features_to_extract = [
        "Sub_Dist_1", "District_1", "District_2", "state_co_1", "State_1", "Total_Nu_1", "Total_Po_1", "Average__1", "Total_Ge_1", "Forest_A_1", "Area_und_1",  "Subdistric",
    ]
    
    convert_geojson_to_csv(
        input_file='subdistrict_updated.geojson',
        output_file='subdistrict_updated.csv',
        selected_features=features_to_extract
    )