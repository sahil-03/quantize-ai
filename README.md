Video demo: https://youtu.be/QjQtyE1QsWc

# Quick Setup Guide

**Hey there, new Quantize.ai Dev :smile:. Welcome to the team! We're thrilled to have you onboard. Here are some instructions to set up your environment!**

1. Create a virtual environment:
python -m venv venv

2. Activate the virtual environment:
- Windows:

venv\Scripts\activate

- Mac/Linux:
source venv/bin/activate


3. Install requirements:
pip install -r requirements.txt

4. Set Python environment variables:
bash
export PYTHONPATH=$(pwd)   

5. Download a Llama model:
- Visit HuggingFace Hub and download a compatible Llama model
- Place it in a directory (e.g., `/app/model` or set `MODEL_DIR` environment variable)

6. Run the inference server:
bash
python core/inference_scripts/llama_inference.py


7. Test the server (in a new terminal):
bash
python core/inference_scripts/test_llama_inference.py

Note: Make sure you have Python 3.8+ installed before starting. The server runs on port 8000 by default.

# Important Links
- Team milestones (team assignments): https://github.com/StanfordCS194/win25-Team21/milestones
- Course Syllabus (accurate assignment deadlines and schedule): https://docs.google.com/spreadsheets/d/1Y5Lcy-f3GsL_aUVHTDTYkmbaJQqK7sEhrNU9xM57UpQ/edit?usp=sharing
- Product Requirements Document: https://docs.google.com/document/d/1E0pHg89MjpcRRoD_MGTppDRUFwhps5ikGwpwc3lIPn4/edit?usp=sharing
- Test Plan: https://docs.google.com/document/d/1hDinHUwIE9mlpdSh3IuQ0AGrR28qy-NGDa3SHJLGyIo/edit?usp=sharing

## Objectives and Key Results (OKRs)

### **OKR 1: Optimize ML Model Inference Efficiency and Cost Savings**

| **OKR Element** | **Description** | **Score and Notes** |
|-----------------|-----------------|---------------------|
| **O**         | **Optimize ML Model Inference Efficiency and Cost Savings:** Automate the quantization process for a variety of ML models to reduce inference latency and compute costs while maintaining near-baseline accuracy. This objective addresses the development and knowledge barriers by ensuring that our quantization process yields models that run efficiently on affordable compute without a significant performance penalty. | Score: 0.0 <br> Notes: Focus on diverse model architectures and document any performance trade-offs. |
| **KR1**       | **Quantize and deploy at least 3 diverse models** with no more than a 5% performance drop relative to their full-precision versions. This KR verifies that our core quantization technique works across different architectures. | Score: 0.0 <br> Notes: Benchmark each model’s accuracy pre- and post-quantization; aim for ≤5% degradation. |
| **KR2**       | **Reduce average inference latency by 30%** compared to legacy inference systems. Faster responses improve user experience and overall system throughput. | Score: 0.0 <br> Notes: Use latency monitoring tools to compare current response times against optimized deployments. |
| **KR3**       | **Achieve a 25% reduction in compute cost per inference** by optimizing resource allocation and scaling strategies. This supports cost savings for users who might otherwise face high compute costs. | Score: 0.0 <br> Notes: Track compute usage and cost data before and after optimization; compare against established cost benchmarks. |

---

### **OKR 2: Enhance Deployment Experience and Scalability**

| **OKR Element** | **Description** | **Score and Notes** |
|-----------------|-----------------|---------------------|
| **O**         | **Enhance Deployment Experience and Scalability:** Streamline the transition from model weight upload to a production-ready, scalable endpoint. This objective aims to reduce the time and complexity in deploying optimized models while ensuring a high-quality user experience. | Score: 0.0 <br> Notes: Emphasize automation, user satisfaction, and multi-cloud support in design. |
| **KR1**       | **Reduce deployment time by 50%** through full automation and integration with container orchestration (e.g., Docker/Kubernetes). Faster deployments mean users can iterate and scale models more rapidly. | Score: 0.0 <br> Notes: Compare current deployment timelines with the new automated pipeline; use time-tracking metrics. |
| **KR2**       | **Achieve a beta user satisfaction score of at least 90%** regarding ease-of-use and reliability of the deployment process. High user satisfaction is critical for adoption and continuous use. | Score: 0.0 <br> Notes: Gather feedback via structured surveys during beta testing; focus on ease-of-use, error rates, and overall experience. |
| **KR3**       | **Integrate automatic scaling across at least 2 major cloud platforms (AWS and GCP)** within the first six months post-launch. This ensures that our solution can handle heterogeneous compute clusters and dynamic loads. | Score: 0.0 <br> Notes: Document integration milestones and monitor performance during scaling tests; measure time-to-scale and stability across platforms. |

---

## Key Performance Indicators (KPIs)

| **KPI**                           | **Details**                                                                                                                                                      | **Relevant Metrics and Notes**                                                                                                                                                                                                                                                 |
|-----------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Daily Inference Volume**        | The total number of inference requests processed per day.                                                                                                      | *North Star metric*: Monitor growth in daily inferences to gauge platform adoption and overall usage. Benchmark current usage and set progressive targets (e.g., increasing by X% month-over-month).                                                                           |
| **Average Inference Latency**     | The mean response time across all inference requests.                                                                                                          | Lower latency indicates improved performance. Track using real-time monitoring tools; target a 30% reduction compared to legacy systems.                                                                                                                                        |
| **Compute Cost per Inference**    | The average cost incurred for processing a single inference request.                                                                                           | A direct measure of cost efficiency. Compare cost before and after implementing quantization; target a 25% reduction. Useful for cost-benefit analysis and pricing strategy.                                                                                                 |
| **Deployment Success Rate**       | Percentage of deployments completed without critical errors or rollbacks.                                                                                        | Reflects the reliability of the deployment pipeline. Target a success rate of 95% or higher; monitor error logs and deployment metrics to identify issues early.                                                                                                             |
| **User Satisfaction & Retention** | Beta user satisfaction scores combined with the percentage of users returning within a defined period (e.g., the first month post-deployment).                  | High satisfaction and retention indicate an excellent user experience. Use surveys and usage data; target a satisfaction score of 90% and retention rates above a set benchmark (e.g., 80% returning users).                                                                   |
| **Model Performance Degradation** | The percentage drop in key model performance metrics (such as accuracy) after applying quantization techniques.                                                 | This KPI ensures that the quantization process preserves model quality. Target a degradation of no more than 5%; regularly compare performance metrics between quantized models and their full-precision counterparts.                                                       |
| **Time to Scale**                 | The duration required for the platform to automatically adjust compute resources in response to increased load.                                                   | Measures the platform’s scalability and agility. Use load testing data to determine responsiveness; aim for scaling adjustments to occur within minutes under peak load conditions.                                                                                        |
