from airllm import AutoModel

class Llama3Service:
    def __init__(self, model_name="v2ray/Llama-3-70B", max_length=128, max_new_tokens=50):
        """
        Initialize the Llama3Service with a pre-trained model.
        :param model_name: Hugging Face model identifier.
        :param max_length: Maximum input length for tokenization.
        :param max_new_tokens: Maximum tokens to generate in the output.
        """
        self.model_name = model_name
        self.max_length = max_length
        self.max_new_tokens = max_new_tokens
        
        # Load the pre-trained model
        print(f"Loading model: {self.model_name}...")
        self.model = AutoModel.from_pretrained(self.model_name)
        print("Model loaded successfully!")

    def generate_response(self, input_text):
        """
        Generate a response for the given input text.
        :param input_text: Input text to the model.
        :return: Generated response as a string.
        """
        try:
            # Tokenize the input text
            input_tokens = self.model.tokenizer(
                input_text,
                return_tensors="pt",
                return_attention_mask=False,
                truncation=True,
                max_length=self.max_length,
                padding=False
            )

            # Generate the response
            generation_output = self.model.generate(
                input_tokens['input_ids'].cuda(),
                max_new_tokens=self.max_new_tokens,
                use_cache=True,
                return_dict_in_generate=True
            )

            # Decode the output tokens into text
            output = self.model.tokenizer.decode(generation_output.sequences[0], skip_special_tokens=True)
            return output
        except Exception as e:
            print(f"Error generating response: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Initialize the service
    llama_service = Llama3Service()

    # Input text
    input_text = "What is the capital of France?"

    # Generate and print the response
    response = llama_service.generate_response(input_text)
    print("Model Response:", response)