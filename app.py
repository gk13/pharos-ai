from flask import Flask, request, jsonify
from transformers import BioGptTokenizer, BioGptForCausalLM
import torch

app = Flask(__name__)

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


FALLBACK_DATABASE = { #In case model responds with unsatisfactory response
    "glaucoma": "Use eye drops such as latanoprost to reduce intraocular pressure.",
    "anxiety": "Consider SSRIs like sertraline or cognitive behavioral therapy.",
    "lung cancer": "Treatment may include surgery, chemotherapy, or targeted therapy depending on the stage.",
    "diabetes": "Manage with insulin therapy, metformin, or lifestyle changes like diet and exercise.",
    "hypertension": "Use ACE inhibitors like lisinopril and maintain a low-sodium diet.",
    "depression": "Consider antidepressants like fluoxetine or psychotherapy.",
    "asthma": "Use an inhaler with albuterol for acute symptoms and inhaled corticosteroids for long-term control.",
    "migraine": "Use triptans like sumatriptan for acute attacks and beta-blockers for prevention.",
    "arthritis": "Manage with NSAIDs like ibuprofen or physical therapy.",
    "pneumonia": "Treat with antibiotics like amoxicillin and ensure adequate rest and hydration."
}    

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    if not data or 'disease' not in data:
        return jsonify({'error': 'Please provide a disease in the request body'}), 400
    
    disease = data['disease'].lower()
    if model is None or tokenizer is None:
        print("Model or tokenizer not loaded, falling back to database")
        if disease in FALLBACK_DATABASE:
            return jsonify({'disease': disease, 'treatment': TREATMENT_DATABASE[disease]})
        return jsonify({'error': 'Model not loaded and disease not found in database'}), 500

    treatment = generate_treatment(disease)

    if is_sensible_treatment(treatment):
        return jsonify({'disease': disease, 'treatment': treatment})
    else:
        print(f"Generated treatment '{treatment}' is not sensible, falling back to database")
        if disease in FALLBACK_DATABASE:
            return jsonify({'disease': disease, 'treatment': TREATMENT_DATABASE[disease]})
        return jsonify({'disease': disease, 'treatment': treatment, 'warning': 'Generated treatment may not be accurate'})

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
            early_stopping=True,  
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    treatment = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if treatment.startswith(input_text):
        treatment = treatment[len(input_text):].strip()
    return treatment

def is_sensible_treatment(treatment):
    treatment = treatment.strip('"')

    if any(phrase in treatment.lower() for phrase in [
        "is a disease", "is a condition", "i am", "refers to", "is characterized by",
        "systematic review", "meta-analysis", "recent advances", "update from", "et al"
    ]):
        return False
    
    if any(phrase in treatment.lower() for phrase in [
        "use ", "treat with", "manage with", "consider ", "recommend ", "prescribe ",
        "therapy", "medication", "lifestyle", "surgery", "diet", "exercise"
    ]):
        return True
    
    return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)