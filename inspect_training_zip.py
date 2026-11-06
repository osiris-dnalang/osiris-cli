#!/usr/bin/env python3
"""
Inspect sample 3MF models from the training archive.
"""
import zipfile
import io
import json
import sys

ZIP_PATH = r"C:\Users\Ron\Desktop\3d-model-training-and-customizing-for-osiris.zip"

def inspect():
    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        infolist = z.infolist()
        three_mf_files = [x for x in infolist if x.filename.endswith('.3mf')]
        print(f"Total .3mf archives: {len(three_mf_files)}")
        
        # Check 5 varied models
        for i, sample in enumerate(three_mf_files[:5]):
            safe_name = sample.filename.encode('ascii', 'replace').decode('ascii')
            print(f"\n[{i+1}] {safe_name} ({sample.file_size} B)")
            data = z.read(sample)
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as sub_z:
                    names = sub_z.namelist()
                    models = [n for n in names if n.startswith('3D/') and n.endswith('.model')]
                    configs = [n for n in names if 'Metadata/' in n]
                    print(f"    3D Models: {len(models)}, Metadata items: {len(configs)}")
                    if 'Metadata/project_settings.config' in names:
                        cfg_raw = sub_z.read('Metadata/project_settings.config').decode('utf-8', errors='ignore')
                        print(f"    Has project_settings.config ({len(cfg_raw)} chars)")
            except Exception as e:
                print(f"    Could not read as zip: {e}")

if __name__ == "__main__":
    inspect()
