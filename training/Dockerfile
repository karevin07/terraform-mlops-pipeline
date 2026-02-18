FROM public.ecr.aws/lambda/python:3.12

# Install build dependencies
RUN dnf update -y && \
    dnf install -y gcc-c++ && \
    dnf clean all

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy function code
COPY train.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "train.lambda_handler" ]
