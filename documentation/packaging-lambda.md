# Building and Packaging Lambda Functions
 
Each Lambda function must be packaged with its dependencies before deployment. Shared dependencies live in `operations/common/` and must be copied into each operation folder before zipping.
 
```bash
# 1. Copy shared dependencies into the operation folder
cp -r app/lambda/operations/common/PyPDF2 app/lambda/operations/merge/
cp -r app/lambda/operations/common/pypdf2-3.0.1.dist-info app/lambda/operations/merge/
 
# 2. Zip the contents
cd app/lambda/operations/merge
zip -r lambda-function.zip .
 
# 3. Clean up copied dependencies
rm -rf PyPDF2 pypdf2-3.0.1.dist-info
```
 
> **Note:** The zip must be created from **inside** the operation folder so that `lambda_function.py` is at the root of the archive — not nested in a subdirectory.
