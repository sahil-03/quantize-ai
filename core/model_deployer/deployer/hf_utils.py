def extract_repo_id(model_path: str) -> str:
        if model_path.startswith("https://huggingface.co/"):
            parts = model_path.rstrip("/").split("/")
            if len(parts) >= 5:
                return f"{parts[3]}/{parts[4]}"
            return model_path
        return model_path