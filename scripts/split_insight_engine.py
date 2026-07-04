import ast
import os

SOURCE_FILE = 'app/services/interpretation_service.py'
INSIGHT_ENGINE_DIR = 'app/insight_engine'

# Map functions to target files
MAPPING = {
    'domains/marriage.py': ['interpret_marriage_prashna', 'detect_marriage_intent'],
    'domains/education.py': ['interpret_education_prashna', 'detect_education_intent', 'cognitive_filter', 'analyze_education_lords', 'education_obstacles', 'education_foundation', 'education_karakas', 'd24_dignity', 'education_verdict_from_score', 'education_timing_from_yoga'],
    'domains/child.py': ['interpret_child_prashna', 'detect_child_intent', 'fertility_sign_check', 'child_creation_bridge', 'best_child_yoga', 'child_afflictions', 'child_family_support', 'child_karakas', 'd7_lineage_stability', 'child_verdict_from_score', 'child_timing_from_yoga'],
    'domains/illness.py': ['interpret_illness_prashna', 'detect_illness_intent', 'illness_vitality_baseline', 'illness_category', 'illness_progression', 'treatment_pillars', 'disease_pillars', 'illness_karakas', 'd6_hidden_source', 'd6_root_meaning', 'illness_verdict_from_score', 'illness_timing_from_yoga'],
    'domains/foreign.py': ['interpret_foreign_prashna', 'detect_foreign_intent', 'foreign_target_house', 'travel_root_anchor', 'travel_destination_bridge', 'best_travel_yoga', 'travel_roadblocks', 'travel_karakas', 'd4_d9_travel_stability', 'foreign_verdict_from_score', 'foreign_timing_from_yoga'],
    'domains/career.py': ['interpret_government_job_prashna', 'detect_government_job_intent', 'government_solar_authority', 'government_competition_selection', 'best_government_yoga', 'government_roadblocks', 'government_karakas', 'd10_government_career', 'government_job_verdict_from_score', 'government_timing_from_yoga', 'interpret_private_job_prashna', 'detect_private_job_intent', 'private_capability_filter', 'private_contract_bridge', 'best_private_job_yoga', 'private_compensation_check', 'private_job_karakas', 'd10_private_career', 'private_job_verdict_from_score', 'private_job_timing_from_yoga'],
    'domains/wealth.py': ['interpret_wealth_prashna', 'detect_wealth_intent', 'wealth_motive_check', 'wealth_flow_support', 'wealth_house_factor', 'best_wealth_yoga', 'wealth_leakage', 'wealth_dignity', 'wealth_karakas', 'd4_wealth_stability', 'wealth_verdict_from_score', 'wealth_timing_from_yoga'],
    'core.py': ['build_interpretation', 'normalized_question_domain', 'infer_question_domain', 'infer_job_subdomain', 'interpret_general_prashna', 'general_vitality', 'general_success', 'best_general_yoga', 'general_obstacles', 'general_verdict_from_score'],
    'rules/common.py': ['planet_strength_score', 'unique_planets', 'authenticity_check', 'analyze_primary_lords', 'house_support', 'karaka_support', 'd9_dignity', 'best_bridge', 'applying_yoga', 'gap_is_widening', 'aspect_between', 'aspect_gap', 'timing_from_yoga', 'verdict_from_score', 'confidence_label', 'aspect_name', 'ordinal', 'item']
}

def extract_imports_and_constants(lines):
    header = []
    for line in lines:
        if line.startswith('def '):
            break
        header.append(line)
    return "".join(header)

def split_file():
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        source_code = f.read()
        
    tree = ast.parse(source_code)
    
    # Store function definitions as strings
    functions_code = {}
    
    source_lines = source_code.splitlines(True)
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            start_lineno = node.lineno - 1
            idx = tree.body.index(node)
            if idx + 1 < len(tree.body):
                end_lineno = tree.body[idx + 1].lineno - 1
                while end_lineno > 0 and source_lines[end_lineno - 1].strip() == '':
                    end_lineno -= 1
            else:
                end_lineno = len(source_lines)
            
            if node.decorator_list:
                start_lineno = node.decorator_list[0].lineno - 1
                
            func_str = "".join(source_lines[start_lineno:end_lineno])
            functions_code[node.name] = func_str
            
    header_code = extract_imports_and_constants(source_lines)
    
    os.makedirs(os.path.join(INSIGHT_ENGINE_DIR, 'domains'), exist_ok=True)
    os.makedirs(os.path.join(INSIGHT_ENGINE_DIR, 'rules'), exist_ok=True)
    
    # Write common.py
    with open(os.path.join(INSIGHT_ENGINE_DIR, 'rules/common.py'), 'w', encoding='utf-8') as f:
        f.write(header_code)
        for func_name in MAPPING['rules/common.py']:
            if func_name in functions_code:
                f.write(functions_code[func_name])
                f.write("\n")
                
    # Write domains and core
    for file_path, func_names in MAPPING.items():
        if file_path == 'rules/common.py':
            continue
            
        with open(os.path.join(INSIGHT_ENGINE_DIR, file_path), 'w', encoding='utf-8') as f:
            f.write(header_code)
            f.write("from app.insight_engine.rules.common import *\n\n")
            
            for func_name in func_names:
                if func_name in functions_code:
                    f.write(functions_code[func_name])
                    f.write("\n")

if __name__ == '__main__':
    split_file()
    print("Successfully split interpretation_service.py into insight_engine module.")
