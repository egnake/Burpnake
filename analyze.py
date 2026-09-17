import os
import ast

def analyze_directory(directory):
    report = []
    for root, dirs, files in os.walk(directory):
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    
                    report.append(f"File: {filepath}")
                    report.append(f"  Lines: {len(content.splitlines())}")
                    report.append(f"  Classes: {', '.join(classes) if classes else 'None'}")
                    report.append(f"  Functions: {len(functions)}")
                    
                    # Basic checks
                    if "print(" in content:
                        report.append("  Warning: Uses print() instead of logger")
                    if "except Exception:" in content or "except Exception as e:" in content:
                        report.append("  Warning: Broad exception handling found")
                    if "os.system" in content or "subprocess" in content:
                        report.append("  Warning: System calls found")
                except Exception as e:
                    report.append(f"File: {filepath} - ERROR parsing: {e}")
    return "\n".join(report)

if __name__ == '__main__':
    res = analyze_directory('app')
    with open('codebase_analysis.txt', 'w', encoding='utf-8') as f:
        f.write(res)
    print("Analysis complete")