---
tags: [атакер, ingested]
source: https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/
---

# LLM04 Data and Model Poisoning

> Источник: https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/

LLM04:2025 Data and Model Poisoning - OWASP Gen AI Security Project Skip to content 
LLM04:2025 Data and Model Poisoning 

Data poisoning occurs when pre-training, fine-tuning, or embedding data is manipulated to introduce vulnerabilities, backdoors, or biases. This manipulation can compromise model security, performance, or ethical behavior, leading to harmful outputs or impaired capabilities. Common risks include degraded model performance, biased or toxic content, and exploitation of downstream systems. 

Data poisoning can target different stages of the LLM lifecycle, including pre-training (learning from general data), fine-tuning (adapting models to specific tasks), and embedding (converting text into numerical vectors). Understanding these stages helps identify where vulnerabilities may originate. Data poisoning is considered an integrity attack since tampering with training data impacts the model’s ability to make accurate predictions. The risks are particularly high with external data sources, which may contain unverified or malicious content. 

Moreover, models distributed through shared repositories or open-source platforms can carry risks beyond data poisoning, such as malware embedded through techniques like malicious pickling, which can execute harmful code when the model is loaded. Also, consider that poisoning may allow for the implementation of a backdoor. Such backdoors may leave the model’s behavior untouched until a certain trigger causes it to change. This may make such changes hard to test for and detect, in effect creating the opportunity for a model to become a sleeper agent. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#common-examples-of-vulnerability] Common Examples of Vulnerability 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#common-examples-of-vulnerability] 
Malicious actors introduce harmful data during training, leading to biased outputs. Techniques like “Split-View Data Poisoning” or “Frontrunning Poisoning” exploit model training dynamics to achieve this. (Ref. link: [https://github.com/GangGreenTemperTatum/speaking/blob/main/dc604/hacker-summer-camp-23/Ads%20_%20Poisoning%20Web%20Training%20Datasets%20_%20Flow%20Diagram%20-%20Exploit%201%20Split-View%20Data%20Poisoning.jpeg] Split-View Data Poisoning ) (Ref. link: [https://github.com/GangGreenTemperTatum/speaking/blob/main/dc604/hacker-summer-camp-23/Ads%20_%20Poisoning%20Web%20Training%20Datasets%20_%20Flow%20Diagram%20-%20Exploit%202%20Frontrunning%20Data%20Poisoning.jpeg] Frontrunning Poisoning ) 

Attackers can inject harmful content directly into the training process, compromising the model’s output quality. 

Users unknowingly inject sensitive or proprietary information during interactions, which could be exposed in subsequent outputs. 

Unverified training data increases the risk of biased or erroneous outputs. 

Lack of resource access restrictions may allow the ingestion of unsafe data, resulting in biased outputs. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#prevention-and-mitigation-strategies] Prevention and Mitigation Strategies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#prevention-and-mitigation-strategies] 
Track data origins and transformations using tools like OWASP CycloneDX or ML-BOM. Verify data legitimacy during all model development stages. 

Vet data vendors rigorously, and validate model outputs against trusted sources to detect signs of poisoning. 

Implement strict sandboxing to limit model exposure to unverified data sources. Use anomaly detection techniques to filter out adversarial data. 

Tailor models for different use cases by using specific datasets for fine-tuning. This helps produce more accurate outputs based on defined goals. 

Ensure sufficient infrastructure controls to prevent the model from accessing unintended data sources. 

Use data version control (DVC) to track changes in datasets and detect manipulation. Versioning is crucial for maintaining model integrity. 

Store user-supplied information in a vector database, allowing adjustments without re-training the entire model. 

Test model robustness with red team campaigns and adversarial techniques, such as federated learning, to minimize the impact of data perturbations. 

Monitor training loss and analyze model behavior for signs of poisoning. Use thresholds to detect anomalous outputs. 

During inference, integrate Retrieval-Augmented Generation (RAG) and grounding techniques to reduce risks of hallucinations. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#example-attack-scenarios] Example Attack Scenarios 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#example-attack-scenarios] 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-1] Attack Scenario #1 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-1] 
An attacker biases the model’s outputs by manipulating training data or using prompt injection techniques, spreading misinformation. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-2] Attack Scenario #2 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-2] 
Toxic data without proper filtering can lead to harmful or biased outputs, propagating dangerous information. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario--3] Attack Scenario # 3 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario--3] 
A malicious actor or competitor creates falsified documents for training, resulting in model outputs that reflect these inaccuracies. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-4] Attack Scenario #4 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-4] 
Inadequate filtering allows an attacker to insert misleading data via prompt injection, leading to compromised outputs. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-5] Attack Scenario #5 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#scenario-5] 
An attacker uses poisoning techniques to insert a backdoor trigger into the model. This could leave you open to authentication bypass, data exfiltration or hidden command execution. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#reference-links] Reference Links 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#reference-links] 
 [https://www.csoonline.com/article/3613932/how-data-poisoning-attacks-corrupt-machine-learning-models.html] How data poisoning attacks corrupt machine learning models : CSO Online 

 [https://atlas.mitre.org/studies/AML.CS0009/] MITRE ATLAS (framework) Tay Poisoning : MITRE ATLAS 

 [https://blog.mithrilsecurity.io/poisongpt-how-we-hid-a-lobotomized-llm-on-hugging-face-to-spread-fake-news/] PoisonGPT: How we hid a lobotomized LLM on Hugging Face to spread fake news : Mithril Security 

 [https://arxiv.org/abs/2305.00944] Poisoning Language Models During Instruction : Arxiv White Paper 2305.00944 

 [https://www.youtube.com/watch?v=h9jf1ikcGyk] Poisoning Web-Scale Training Datasets – Nicholas Carlini | Stanford MLSys #75 : Stanford MLSys Seminars YouTube Video 

 [https://www.darkreading.com/cloud-security/ml-model-repositories-next-big-supply-chain-attack-target] ML Model Repositories: The Next Big Supply Chain Attack Target OffSecML 

 [https://jfrog.com/blog/data-scientists-targeted-by-malicious-hugging-face-ml-models-with-silent-backdoor/] Data Scientists Targeted by Malicious Hugging Face ML Models with Silent Backdoor JFrog 

 [https://towardsdatascience.com/backdoor-attacks-on-language-models-can-we-trust-our-models-weights-73108f9dcb1f] Backdoor Attacks on Language Models : Towards Data Science 

 [https://blog.trailofbits.com/2021/03/15/never-a-dill-moment-exploiting-machine-learning-pickle-files/] Never a dill moment: Exploiting machine learning pickle files TrailofBits 

 [https://www.anthropic.com/news/sleeper-agents-training-deceptive-llms-that-persist-through-safety-training] arXiv:2401.05566 Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training Anthropic (arXiv) 

 [https://www.cobalt.io/blog/backdoor-attacks-on-ai-models] Backdoor Attacks on AI Models Cobalt 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#related-frameworks-and-taxonomies] Related Frameworks and Taxonomies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM04_DataModelPoisoning.md#related-frameworks-and-taxonomies] 
Refer to this section for comprehensive information, scenarios strategies relating to infrastructure deployment, applied environment controls and other best practices. 

 [https://atlas.mitre.org/techniques/AML.T0018] AML.T0018 | Backdoor ML Model MITRE ATLAS 

 [https://www.nist.gov/itl/ai-risk-management-framework] NIST AI Risk Management Framework : Strategies for ensuring AI integrity. NIST 

Share this: 

 [https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/?share=twitter] Share on X (Opens in new window) X 

 [https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/?share=facebook] Share on Facebook (Opens in new window) Facebook 

More 

 [https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/#print?share=print] Print (Opens in new window) Print 

Email a link to a friend (Opens in new window) Email 

 [https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/?share=x] Share on X (Opens in new window) X 

LLM Top 10 
 [https://genai.owasp.org/llmrisk/llm01-prompt-injection/] 
LLM01:2025 Prompt Injection 

A Prompt Injection Vulnerability occurs when user prompts alter the LLM’s behavior or output in unintended ways. These inputs... 
 [https://genai.owasp.org/llmrisk/llm01-prompt-injection/] [https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/] 
LLM02:2025 Sensitive Information Disclosure 

Sensitive information can affect both the LLM and its application context. This includes personal identifiable information (PII), financial details,... 
 [https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/] [https://genai.owasp.org/llmrisk/llm032025-supply-chain/] 
LLM03:2025 Supply Chain 

LLM supply chains are susceptible to various vulnerabilities, which can affect the integrity of training data, models, and deployment... 
 [https://genai.owasp.org/llmrisk/llm032025-supply-chain/] [https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/] 
LLM04:2025 Data and Model Poisoning 

Data poisoning occurs when pre-training, fine-tuning, or embedding data is manipulated to introduce vulnerabilities, backdoors, or biases. This manipulation... 
 [https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/] [https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/] 
LLM05:2025 Improper Output Handling 

Improper Output Handling refers specifically to insufficient validation, sanitization, and handling of the outputs generated by large language models... 
 [https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/] [https://genai.owasp.org/llmrisk/llm062025-excessive-agency/] 
LLM06:2025 Excessive Agency 

An LLM-based system is often granted a degree of agency by its developer – the ability to call functions... 
 [https://genai.owasp.org/llmrisk/llm062025-excessive-agency/] [https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/] 
LLM07:2025 System Prompt Leakage 

The system prompt leakage vulnerability in LLMs refers to the risk that the system prompts or instructions used to... 
 [https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/] [https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/] 
LLM08:2025 Vector and Embedding Weaknesses 

Vectors and embeddings vulnerabilities present significant security risks in systems utilizing Retrieval Augmented Generation (RAG) with Large Language Models... 
 [https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/] [https://genai.owasp.org/llmrisk/llm092025-misinformation/] 
LLM09:2025 Misinformation 

Misinformation from LLMs poses a core vulnerability for applications relying on these models. Misinformation occurs when LLMs produce false... 
 [https://genai.owasp.org/llmrisk/llm092025-misinformation/] [https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/] 
LLM10:2025 Unbounded Consumption 

Unbounded Consumption refers to the process where a Large Language Model (LLM) generates outputs based on input queries or... 
 [https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/] Scroll to Top 
LLM04:2025 Data and Model Poisoning
