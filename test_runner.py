import os
import importlib

def discover_and_run_tests():
    test_results = []
    for filename in os.listdir(os.path.dirname(__file__)):
        if filename.startswith('test_') and filename.endswith('.py'):
            modulename = filename[:-3]
            module = importlib.import_module(modulename)
            if hasattr(module, 'run_tests'):
                result = module.run_tests()
                test_results.append((modulename, result))
    return test_results

if __name__ == "__main__":
    results = discover_and_run_tests()
    for modulename, result in results:
        print(f"{modulename}: {result}")
    if not results:
        print("No test modules found.")
