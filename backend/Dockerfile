# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the dependencies file to the working directory
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the backend code into the container
COPY . .

# 6. Make port 8000 available to the world outside this container
EXPOSE 8000

# 7. Run uvicorn server when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]