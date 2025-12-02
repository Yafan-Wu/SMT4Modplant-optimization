# SMT4ModPlant

## Overview
SMT4ModPlant is an open-source Python framework for semantic-driven feasibility checking and configuration of modular plants. The framework integrates semantic process and resource descriptions, automated transformation into formal SMT constraints, and logic-based validation of resource assignments using the Z3 SMT solver.

## Features
- **Semantic parsing** of general process recipes (BatchML) and resource descriptions (AAS XML, Capability Description Submodel)
- **Automatic mapping** of required and offered capabilities using ontology-based identifiers (Semantic descriptions)
- **Generation of SMT-LIB models** encoding all assignment, property, and material flow constraints
- **Automated feasibility checking** of resource-to-step assignments, property compatibility, and material flow consistency
- **Debugging and traceability support** using named assertions and unsat-core analysis
- **Reproducible example data** for all experimental results (Example general recipe and resources HC10, HC20 and HC30)

## Repository Structure

SMT4ModPlant/
- GeneralRecipeParser.py                     - (Parser for BatchML general recipes)
- AASxmlCapabilityParser.py                  - (Parser for AAS-based resource descriptions)
- SMT4ModPlant_main.py                       - (Main script: SMT model generation & solver integration)
- ExampleGeneralRecipe.xml                   - (Example BatchML general recipe (case study))
- HC10.xml / HC20.xml / HC30.xml             - (Resource capability descriptions (AAS XML))
- parsed_recipe_output.json                  - (Parsed general recipe (JSON))
- parsed_resource_capabilities_output.json   - (Parsed resource capabilities description (JSON))
- modell_annotated.smt2                      - (Annotated SMT-LIB model (generated))
- README.md                                  
- LICENSE

## Getting Started
- Execute **SMT4ModPlant_main.py** and provide input files **_parsed_recipe_output.json_** and **_parsed_resource_capabilities_output.json_**

### Requirements

- Python 3.8+
- [Z3 SMT Solver](https://github.com/Z3Prover/z3) (Python bindings; install via `pip install z3-solver`)
- Standard Python libraries (`json`, `xml.etree`, etc.)

### Usage


1. **Parse recipe and resource data:**

   ```bash
   python GeneralRecipeParser.py ExampleGeneralRecipe.xml parsed_recipe_output.json
   python AASxmlCapabilityParser.py HC10.xml HC20.xml HC30.xml parsed_resource_capabilities_output.json
   ```

2. **Generate and check SMT model:**
     ```bash
     python z3CheckSatisfiability.py
     ```
    This will generate _modell_annotated.smt2_ and print/record assignment results.

3. **Review the results:**
- Feasible assignments in the command line console
- Annotated SMT-LIB model in _modell_annotated.smt2_
- All intermediate data and example files are included for reproduction

## Example

The repository includes an example for a modular process with three resources (HC10, HC20, HC30) and steps (MixingOfLiquids, Dosing, HeatingOfLiquids). The solver output contains assignment explanations.

## License
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Contact
- Michael Winter
- Chair of Information and Automation Systems for Process and Materials Engineering (IAT), RWTH Aachen University

## Acknowledgments
- Development supported by RWTH Aachen University, IAT
- Open-source dependencies: Z3 SMT Solver, Python

For questions, issues, or feedback, please open an issue or contact the authors.
