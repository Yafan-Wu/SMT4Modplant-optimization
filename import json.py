import json
import uuid
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

def load_data_files():
    """加载所有需要的JSON文件"""
    with open('parsed_resource_capabilities_output.json', 'r') as f:
        resources = json.load(f)
    
    with open('solutions.json', 'r') as f:
        solutions = json.load(f)
    
    with open('optimization_report.json', 'r') as f:
        optimization = json.load(f)
    
    with open('parsed_recipe_output.json', 'r') as f:
        general_recipe = json.load(f)
    
    return resources, solutions, optimization, general_recipe

def generate_b2mml_master_recipe(resources, solutions, optimization, general_recipe):
    # 获取最优解（solution_id=4）
    optimal_solution_id = optimization['optimal_solution']['solution_id']
    optimal_solution = None
    for solution in solutions['solutions']:
        if solution['solution_id'] == optimal_solution_id:
            optimal_solution = solution
            break
    
    if not optimal_solution:
        raise ValueError(f"Optimal solution {optimal_solution_id} not found in solutions.json")
    
    # 创建XML根元素
    root = ET.Element('b2mml:BatchInformation', 
                     attrib={
                         'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                         'xsi:schemaLocation': 'http://www.mesa.org/xml/B2MML Schema/AllSchemas.xsd',
                         'xmlns:b2mml': 'http://www.mesa.org/xml/B2MML'
                     })
    
    # ListHeader
    list_header = ET.SubElement(root, 'b2mml:ListHeader')
    ET.SubElement(list_header, 'b2mml:ID').text = 'ListHeadID'
    ET.SubElement(list_header, 'b2mml:CreateDate').text = datetime.now().isoformat() + '+01:00'
    
    # Description
    desc = ET.SubElement(root, 'b2mml:Description')
    desc.text = f"This Batch Information includes the Master Recipe based on General Recipe {general_recipe['ID']} and Optimal Solution {optimal_solution_id}"
    
    # MasterRecipe
    master_recipe = ET.SubElement(root, 'b2mml:MasterRecipe')
    ET.SubElement(master_recipe, 'b2mml:ID').text = f"MasterRecipe_{optimal_solution_id}"
    ET.SubElement(master_recipe, 'b2mml:Version').text = '1.0.0'
    ET.SubElement(master_recipe, 'b2mml:VersionDate').text = datetime.now().isoformat() + '+01:00'
    
    recipe_desc = ET.SubElement(master_recipe, 'b2mml:Description')
    recipe_desc.text = f"Master recipe based on General Recipe {general_recipe['ID']} and optimized solution {optimal_solution_id} using resources from optimization"
    
    # Header
    header = ET.SubElement(master_recipe, 'b2mml:Header')
    ET.SubElement(header, 'b2mml:ProductID').text = 'StirredHeatedWater'
    ET.SubElement(header, 'b2mml:ProductName').text = 'Stirred and Heated Water'
    
    # EquipmentRequirement
    equipment_req = ET.SubElement(master_recipe, 'b2mml:EquipmentRequirement')
    ET.SubElement(equipment_req, 'b2mml:ID').text = 'Equipment Requirement for the HCs'
    
    constraint = ET.SubElement(equipment_req, 'b2mml:Constraint')
    ET.SubElement(constraint, 'b2mml:ID').text = 'Material constraint'
    ET.SubElement(constraint, 'b2mml:Condition').text = 'Material == H2O'
    
    ET.SubElement(equipment_req, 'b2mml:Description').text = 'Only water is allowed for the stirring and heating process'
    
    # Formula - 收集所有参数
    formula = ET.SubElement(master_recipe, 'b2mml:Formula')
    
    # 辅助函数：从资源数据中查找propertyRealizedBy
    def find_property_realized_by(resource_name, capability_name, property_name):
        if resource_name not in resources:
            return None
        
        for capability_data in resources[resource_name]:
            # 检查capability名称
            cap_match = False
            for cap in capability_data['capability']:
                if cap['capability_name'] == capability_name:
                    cap_match = True
                    break
            
            if not cap_match:
                continue
            
            # 在properties中查找
            for prop in capability_data['properties']:
                if prop.get('property_name') == property_name:
                    return prop.get('propertyRealizedBy')
            
            # 如果没有找到，检查是否是通用属性
            for prop in capability_data.get('properties', []):
                # 尝试通过ID匹配
                if prop.get('property_name', '').lower() == property_name.lower():
                    return prop.get('propertyRealizedBy')
        
        return None
    
    # 映射数据类型
    def map_data_type(json_type):
        mapping = {
            'xs:int': 'integer',
            'xs:double': 'double',
            'int': 'integer',
            'double': 'double',
            'duration': 'duration'
        }
        return mapping.get(json_type, json_type)
    
    # 映射单位
    def map_unit(unit_uri):
        mapping = {
            'http://si-digital-framework.org/SI/units/second': 'Sekunde',
            'http://si-digital-framework.org/SI/units/litre': 'Liter',
            'http://si-digital-framework.org/SI/units/degreeCelsius': 'Grad Celsius',
            'http://qudt.org/vocab/unit/REV-PER-MIN': 'Umdrehungen pro Minute',
            'http://qudt.org/vocab/unit/PERCENT': 'Prozent',
            'http://qudt.org/vocab/unit/CYC-PER-SEC': 'Zyklen pro Sekunde'
        }
        return mapping.get(unit_uri, unit_uri.split('/')[-1] if '/' in unit_uri else unit_uri)
    
    # 存储参数映射 - 全局参数计数器
    param_mapping = {}
    global_param_counter = 1
    
    # 先处理所有参数，为每个参数分配唯一的ID
    for pe in general_recipe['ProcessElements']:
        # 在最优解中查找对应的assignment
        assignment = None
        for a in optimal_solution['assignments']:
            if a['step_id'] == pe['ID']:
                assignment = a
                break
        
        if not assignment:
            continue
        
        # 处理每个参数
        for param in pe['Parameters']:
            # 生成参数ID
            param_id = None
            
            # 对于Dosing的特殊处理
            if pe['ID'] == 'Dosing001' and param['ID'] == 'Dosing_Amount001':
                # 剂量使用liter单位，查找Litre属性的propertyRealizedBy
                property_realized_by = find_property_realized_by(
                    assignment['resource'], 
                    'Dosing', 
                    'Litre'
                )
                param_id = property_realized_by
            
            else:
                # 在capability_details中查找匹配的属性
                for capability_detail in assignment.get('capability_details', []):
                    for matched_prop in capability_detail.get('matched_properties', []):
                        # 检查Key和Unit是否匹配
                        if (matched_prop.get('property_id') == param['Key'] and 
                            matched_prop.get('property_unit') == param['UnitOfMeasure']):
                            # 使用property_name在资源中查找propertyRealizedBy
                            property_realized_by = find_property_realized_by(
                                assignment['resource'], 
                                capability_detail['capability_name'], 
                                matched_prop.get('property_name')
                            )
                            param_id = property_realized_by
                            break
                    
                    if param_id:
                        break
            
            # 如果没有找到propertyRealizedBy，使用null
            if not param_id:
                param_id = 'null'
            
            # 格式化参数ID - 使用全局计数器
            formatted_param_id = f"{global_param_counter:03d}:{param_id}"
            param_mapping[param['ID']] = formatted_param_id
            
            # 创建Parameter元素
            param_elem = ET.SubElement(formula, 'b2mml:Parameter')
            ET.SubElement(param_elem, 'b2mml:ID').text = formatted_param_id
            
            # 生成描述
            resource_short = assignment['resource'].replace('resource: ', '').replace('2025-04_', '')
            param_desc = f"{resource_short}_{param['Description'].replace(' ', '_')}"
            ET.SubElement(param_elem, 'b2mml:Description').text = param_desc
            
            ET.SubElement(param_elem, 'b2mml:ParameterType').text = 'ProcessParameter'
            ET.SubElement(param_elem, 'b2mml:ParameterSubType').text = 'ST'
            
            value_elem = ET.SubElement(param_elem, 'b2mml:Value')
            # 处理比较操作符（>=, <=）
            value_str = param['ValueString']
            if value_str.startswith('>=') or value_str.startswith('<='):
                # 移除比较操作符，只保留数值
                value_str = value_str[2:]
            ET.SubElement(value_elem, 'b2mml:ValueString').text = value_str
            ET.SubElement(value_elem, 'b2mml:DataInterpretation').text = 'Constant'
            ET.SubElement(value_elem, 'b2mml:DataType').text = map_data_type(param['DataType'])
            ET.SubElement(value_elem, 'b2mml:UnitOfMeasure').text = map_unit(param['UnitOfMeasure'])
            
            global_param_counter += 1
    
    # ProcedureLogic
    procedure_logic = ET.SubElement(master_recipe, 'b2mml:ProcedureLogic')
    
    # 创建步骤列表
    steps = []
    
    # 1. 开始步骤
    steps.append({
        'id': 'S1',
        'recipe_element_id': 'Init',
        'description': 'Init'
    })
    
    # 2. 按照ProcessElements的顺序创建操作步骤
    step_counter = 2  # 从S2开始
    recipe_element_counter = 1  # RecipeElement编号计数器
    
    for pe in general_recipe['ProcessElements']:
        step_id = f"S{step_counter}"
        
        # 查找对应的assignment
        assignment = None
        for a in optimal_solution['assignments']:
            if a['step_id'] == pe['ID']:
                assignment = a
                break
        
        if not assignment:
            print(f"Warning: No assignment found for process element {pe['ID']}")
            continue
        
        # 生成RecipeElement ID
        recipe_element_id = None
        resource_short = assignment['resource'].replace('resource: ', '').replace('2025-04_', '')
        
        # 从资源数据中查找realized_by
        if assignment['resource'] in resources:
            for capability_data in resources[assignment['resource']]:
                # 检查是否包含所需的能力
                capabilities_matched = False
                for cap in capability_data['capability']:
                    if cap['capability_name'] in assignment['capabilities']:
                        capabilities_matched = True
                        break
                
                if capabilities_matched and capability_data.get('realized_by'):
                    recipe_element_id = f"{recipe_element_counter:03d}:{capability_data['realized_by'][0]}"
                    break
        
        # 如果没有找到realized_by，使用UUID
        if not recipe_element_id:
            recipe_element_id = f"{recipe_element_counter:03d}:{str(uuid.uuid4())}"
        
        # 生成步骤描述
        step_description = f"{recipe_element_counter:03d}:{resource_short}_{pe['Description']}"
        
        steps.append({
            'id': step_id,
            'recipe_element_id': recipe_element_id,
            'description': step_description,
            'process_element': pe,
            'assignment': assignment,
            'recipe_element_number': recipe_element_counter
        })
        
        # 存储recipe_element_id用于后续创建RecipeElement
        pe['recipe_element_id'] = recipe_element_id
        pe['recipe_element_number'] = recipe_element_counter
        
        step_counter += 1
        recipe_element_counter += 1
    
    # 3. 结束步骤
    steps.append({
        'id': f"S{step_counter}",
        'recipe_element_id': 'End',
        'description': 'End'
    })
    
    # 创建步骤到转换的链接 (4个链接: S1→T1, S2→T2, S3→T3, S4→T4)
    for i in range(len(steps) - 1):  # i = 0,1,2,3 (共4个链接)
        link = ET.SubElement(procedure_logic, 'b2mml:Link')
        ET.SubElement(link, 'b2mml:ID').text = f"L{i+1}"
        
        from_id = ET.SubElement(link, 'b2mml:FromID')
        ET.SubElement(from_id, 'b2mml:FromIDValue').text = steps[i]['id']
        ET.SubElement(from_id, 'b2mml:FromType').text = 'Step'
        ET.SubElement(from_id, 'b2mml:IDScope').text = 'External'
        
        to_id = ET.SubElement(link, 'b2mml:ToID')
        ET.SubElement(to_id, 'b2mml:ToIDValue').text = f"T{i+1}"
        ET.SubElement(to_id, 'b2mml:ToType').text = 'Transition'
        ET.SubElement(to_id, 'b2mml:IDScope').text = 'External'
        
        ET.SubElement(link, 'b2mml:LinkType').text = 'ControlLink'
        ET.SubElement(link, 'b2mml:Depiction').text = 'LineAndArrow'
        ET.SubElement(link, 'b2mml:EvaluationOrder').text = '1'
        ET.SubElement(link, 'b2mml:Description').text = 'string'
    
    # 创建转换到步骤的链接 (4个链接: T1→S2, T2→S3, T3→S4, T4→S5)
    for i in range(1, len(steps)):  # i = 1,2,3,4 (共4个链接)
        link = ET.SubElement(procedure_logic, 'b2mml:Link')
        ET.SubElement(link, 'b2mml:ID').text = f"L{len(steps) + i - 1}"  # L5, L6, L7, L8
        
        from_id = ET.SubElement(link, 'b2mml:FromID')
        ET.SubElement(from_id, 'b2mml:FromIDValue').text = f"T{i}"
        ET.SubElement(from_id, 'b2mml:FromType').text = 'Transition'
        ET.SubElement(from_id, 'b2mml:IDScope').text = 'External'
        
        to_id = ET.SubElement(link, 'b2mml:ToID')
        ET.SubElement(to_id, 'b2mml:ToIDValue').text = steps[i]['id']
        ET.SubElement(to_id, 'b2mml:ToType').text = 'Step'
        ET.SubElement(to_id, 'b2mml:IDScope').text = 'External'
        
        ET.SubElement(link, 'b2mml:LinkType').text = 'ControlLink'
        ET.SubElement(link, 'b2mml:Depiction').text = 'LineAndArrow'
        ET.SubElement(link, 'b2mml:EvaluationOrder').text = '1'
        ET.SubElement(link, 'b2mml:Description').text = 'string'
    
    # 创建步骤元素 (5个步骤)
    for step in steps:
        step_elem = ET.SubElement(procedure_logic, 'b2mml:Step')
        ET.SubElement(step_elem, 'b2mml:ID').text = step['id']
        ET.SubElement(step_elem, 'b2mml:RecipeElementID').text = step['recipe_element_id']
        ET.SubElement(step_elem, 'b2mml:RecipeElementVersion')
        ET.SubElement(step_elem, 'b2mml:Description').text = step['description']
    
    # 创建转换元素 (4个转换)
    for i in range(1, len(steps)):  # i = 1,2,3,4 (共4个转换)
        transition = ET.SubElement(procedure_logic, 'b2mml:Transition')
        ET.SubElement(transition, 'b2mml:ID').text = f"T{i}"
        
        if i == 1:  # T1: 从Init开始
            ET.SubElement(transition, 'b2mml:Condition').text = 'True'
        elif i == len(steps) - 1:  # T4: 到End
            step_desc = steps[i-1]['description']  # 前一个步骤S4的描述
            ET.SubElement(transition, 'b2mml:Condition').text = f"Step {step_desc} is Completed"
        else:  # T2, T3
            step_desc = steps[i-1]['description']  # 前一个步骤的描述（S2, S3）
            ET.SubElement(transition, 'b2mml:Condition').text = f"Step {step_desc} is Completed"
    
    # RecipeElements
    # 1. Begin和End元素
    for elem_type, elem_id in [('Begin', 'Init'), ('End', 'End')]:
        recipe_elem = ET.SubElement(master_recipe, 'b2mml:RecipeElement')
        ET.SubElement(recipe_elem, 'b2mml:ID').text = elem_id
        ET.SubElement(recipe_elem, 'b2mml:RecipeElementType').text = elem_type
    
    # 2. 为每个Process Element创建RecipeElement
    # 按照recipe_element_number排序
    recipe_elements_sorted = sorted(
        [pe for pe in general_recipe['ProcessElements'] if 'recipe_element_number' in pe],
        key=lambda x: x['recipe_element_number']
    )
    
    for pe in recipe_elements_sorted:
        # 查找对应的assignment
        assignment = None
        for a in optimal_solution['assignments']:
            if a['step_id'] == pe['ID']:
                assignment = a
                break
        
        if not assignment:
            continue
        
        recipe_elem = ET.SubElement(master_recipe, 'b2mml:RecipeElement')
        ET.SubElement(recipe_elem, 'b2mml:ID').text = pe['recipe_element_id']
        
        resource_short = assignment['resource'].replace('resource: ', '').replace('2025-04_', '')
        capability_name = assignment['capabilities'][0] if assignment['capabilities'] else 'Unknown'
        
        # 生成描述
        pe_name_map = {
            'Mixing_of_Liquids': 'Mixing',
            'Dosing': 'Dosing',
            'Heating_of_liquids': 'Heating'
        }
        pe_short = pe_name_map.get(pe['Description'], pe['Description'])
        ET.SubElement(recipe_elem, 'b2mml:Description').text = f"{resource_short}_{pe_short}_Procedure"
        
        ET.SubElement(recipe_elem, 'b2mml:RecipeElementType').text = 'Operation'
        ET.SubElement(recipe_elem, 'b2mml:ActualEquipmentID').text = f"{resource_short}Instance"
        
        equipment_req_ref = ET.SubElement(recipe_elem, 'b2mml:EquipmentRequirement')
        ET.SubElement(equipment_req_ref, 'b2mml:ID').text = 'Equipment Requirement for the HCs'
        
        # 添加参数引用
        for param in pe['Parameters']:
            if param['ID'] in param_mapping:
                param_ref = ET.SubElement(recipe_elem, 'b2mml:Parameter')
                ET.SubElement(param_ref, 'b2mml:ID').text = param_mapping[param['ID']]
                ET.SubElement(param_ref, 'b2mml:ParameterType').text = 'ProcessParameter'
    
    # 转换为格式化的XML字符串
    xml_str = ET.tostring(root, encoding='unicode')
    
    # 使用minidom美化输出
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='\t')
    
    return pretty_xml, optimal_solution_id, optimization['optimal_solution']

def save_b2mml_xml(xml_content, filename='MasterRecipe_B2MML.xml'):
    """保存B2MML XML到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f"B2MML Master Recipe saved to {filename}")

def main():
    """主函数"""
    try:
        # 加载数据文件
        print("Loading data files...")
        resources, solutions, optimization, general_recipe = load_data_files()
        
        # 生成B2MML格式的Master Recipe
        print("Generating B2MML Master Recipe...")
        b2mml_xml, optimal_solution_id, optimal_solution_info = generate_b2mml_master_recipe(
            resources, solutions, optimization, general_recipe
        )
        
        # 保存到文件
        save_b2mml_xml(b2mml_xml)
        
        print("\nB2MML Master Recipe Generation Complete!")
        print(f"\nUsing Optimal Solution: {optimal_solution_id}")
        print(f"Composite Score: {optimal_solution_info['composite_score']}")
        
        # 打印一些统计信息
        print("\nResource Usage:")
        for resource, count in optimal_solution_info['resource_usage'].items():
            resource_short = resource.replace('resource: ', '').replace('2025-04_', '')
            print(f"  {resource_short}: {count} step(s)")
        
        print(f"\nTotal Energy Cost: {optimal_solution_info['total_energy_cost']}")
        print(f"Total Use Cost: {optimal_solution_info['total_use_cost']}")
        print(f"Total CO2 Footprint: {optimal_solution_info['total_co2_footprint']}")
        print(f"Material Flow Consistent: {optimal_solution_info['material_flow_consistent']}")
        
        # 打印生成的步骤信息
        print("\nGenerated Steps:")
        print("1. S1: Init (Begin)")
        print("2. S2: Mixing step")
        print("3. S3: Dosing step")
        print("4. S4: Heating step")
        print("5. S5: End (End)")
        
    except FileNotFoundError as e:
        print(f"Error: Required data file not found: {str(e)}")
        print("Please ensure all required JSON files are in the current directory:")
        print("1. parsed_resource_capabilities_output.json")
        print("2. solutions.json")
        print("3. optimization_report.json")
        print("4. parsed_recipe_output.json")
    except Exception as e:
        print(f"Error generating B2MML Master Recipe: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()