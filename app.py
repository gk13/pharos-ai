from flask import Flask, request, jsonify
from transformers import BioGptTokenizer, BioGptForCausalLM
import torch
import asyncio
from proxy_lite import Runner, RunnerConfig

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

model_name = "microsoft/biogpt"

try:
    print("Loading BioGPT tokenizer and model...")
    tokenizer = BioGptTokenizer.from_pretrained(model_name)
    model = BioGptForCausalLM.from_pretrained(model_name)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Failed to load model: {e}")
    model = None
    tokenizer = None

# Use GPU when available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if model is not None:
    model.to(device)
    model.eval()

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    if not data or 'disease' not in data:
        return jsonify({'error': 'Please provide a disease in the request body'}), 400
    
    disease = data['disease'].lower()

    biogpt_treatment = generate_treatment(disease)

    print(f"\033[34mGenerated treatment '{biogpt_treatment}' can be improved, now using Proxy AI\033[0m", flush=True)  #Call to Proxy AI after BioGPT returns response  
    
    # Configure Proxy AI
    config = RunnerConfig.from_dict({
        "environment": {
            "name": "webbrowser",
            "homepage": "https://www.healthline.com",
            "headless": True,  
        },
        "solver": {
            "name": "simple",
            "agent": {
                "name": "proxy_lite",
                "client": {
                    "name": "convergence",
                    "model_id": "convergence-ai/proxy-lite-3b",
                    "api_base": "https://convergence-ai-demo-api.hf.space/v1",  
                },
            },
        },
        "max_steps": 10, 
        "action_timeout": 300,
        "environment_timeout": 600,
        "task_timeout": 1800,
        "logger_level": "INFO",
    })

    proxy_runner = Runner(config=config)
    task = (
    f"First, wait for the page to fully load. If there is a cookie consent popup or a privacy terms screen, "
    f"look for a button with text like 'Accept and Continue to Site', 'Accept', or 'Agree' and click it to dismiss the popup. "
    f"If the button is in a modal dialog or iframe, ensure you interact with the correct frame. "
    f"Then, search for 'treatments for {disease}' on Healthline and extract the recommended treatment in a concise sentence."
)
    
    try:
        run_result = asyncio.run(proxy_runner.run(task))
        if hasattr(run_result, 'output'):
                proxy_treatment = run_result.output
        elif hasattr(run_result, 'result'):
                proxy_treatment = run_result.result
        else:
            # If we can't find the output directly, try to extract it from the logs
            # This is a fallback and might need adjustment based on proxy_lite's behavior
            proxy_treatment = str(run_result)  # Convert the Run object to a string to search for the treatment
            # Look for the task completion message
            if "Task complete" in proxy_treatment:
                # Extract the text after "Task complete. ✨"
                start_idx = proxy_treatment.find("Task complete. ✨") + len("Task complete. ✨")
                proxy_treatment = proxy_treatment[start_idx:].strip()
                # Remove any trailing log messages (e.g., timestamps)
                proxy_treatment = proxy_treatment.split('\n')[0].strip()
            else:
                proxy_treatment = "No treatment found by Proxy AI" 
        # Ensure the treatment is a string and clean it up
        if not isinstance(proxy_treatment, str):
            proxy_treatment = str(proxy_treatment)                    

        return jsonify({
            'disease': disease,
            'biogpt_treatment': biogpt_treatment,
            'proxy_treatment': proxy_treatment
        })
    except Exception as e:
        return jsonify({'error': f"Proxy AI failed: {str(e)}"}), 500
 
def generate_treatment(disease):
    input_text = (
        "As a medical professional, recommend a specific treatment (e.g., medication, therapy, or lifestyle change) "
        "for a patient diagnosed with the following disease in one concise sentence. "
        "For example, for hypertension, you might say: 'Use ACE inhibitors like lisinopril and maintain a low-sodium diet.' "
        f"Now, recommend a treatment for {disease}: "
    )
    inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=160,
            min_length=10,
            do_sample=True,  # Enable sampling for more diversity
            top_k=50,        # Use top-k sampling to balance diversity and quality
            top_p=0.9,       # Use nucleus sampling for better coherence 
            no_repeat_ngram_size=2,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    treatment = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if treatment.startswith(input_text):
        treatment = treatment[len(input_text):].strip()
    return treatment

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)