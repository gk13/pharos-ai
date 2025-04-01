from flask import Flask, request, jsonify
from transformers import BioGptTokenizer, BioGptForCausalLM
import torch

app = Flask(__name__)

# Load pre-trained BioGPT model and tokenizer
model_name = "microsoft/biogpt"
tokenizer = BioGptTokenizer.from_pretrained(model_name)
model = BioGptForCausalLM.from_pretrained(model_name)

# Use GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    if not data or 'disease' not in data:
        return jsonify({'error': 'Please provide a disease in the request body'}), 400
    
    disease = data['disease'].lower()
    treatment = generate_treatment(disease)
    return jsonify({'disease': disease, 'treatment': treatment})

def generate_treatment(disease):
    input_text = f"Treatment for {disease}:"
    inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=512,
            min_length=10,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            no_repeat_ngram_size=3,
            pad_token_id=tokenizer.eos_token_id
        )
    
    treatment = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if treatment.startswith(input_text):
        treatment = treatment[len(input_text):].strip()
    return treatment

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)