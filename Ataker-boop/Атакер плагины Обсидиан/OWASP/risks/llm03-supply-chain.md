---
tags: [атакер, ingested]
source: https://genai.owasp.org/llmrisk/llm032025-supply-chain/
---

# LLM03 Supply Chain

> Источник: https://genai.owasp.org/llmrisk/llm032025-supply-chain/

LLM03:2025 Supply Chain - OWASP Gen AI Security Project Skip to content 
LLM03:2025 Supply Chain 

LLM supply chains are susceptible to various vulnerabilities, which can affect the integrity of training data, models, and deployment platforms. These risks can result in biased outputs, security breaches, or system failures. While traditional software vulnerabilities focus on issues like code flaws and dependencies, in ML the risks also extend to third-party pre-trained models and data. 

These external elements can be manipulated through tampering or poisoning attacks. 

Creating LLMs is a specialized task that often depends on third-party models. The rise of open-access LLMs and new fine-tuning methods like “LoRA” (Low-Rank Adaptation) and “PEFT” (Parameter-Efficient Fine-Tuning), especially on platforms like Hugging Face, introduce new supply-chain risks. Finally, the emergence of on-device LLMs increase the attack surface and supply-chain risks for LLM applications. 

Some of the risks discussed here are also discussed in “LLM04 Data and Model Poisoning.” This entry focuses on the supply-chain aspect of the risks. A simple threat model can be found [https://github.com/jsotiro/ThreatModels/blob/main/LLM%20Threats-LLM%20Supply%20Chain.png] here . 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#common-examples-of-risks] Common Examples of Risks 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#common-examples-of-risks] 
1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#1-traditional-third-party-package-vulnerabilities] Traditional Third-party Package Vulnerabilities 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#1-traditional-third-party-package-vulnerabilities] 
Such as outdated or deprecated components, which attackers can exploit to compromise LLM applications. This is similar to “A06:2021 – Vulnerable and Outdated Components” with increased risks when components are used during model development or finetuning. (Ref. link: [https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/] A06:2021 – Vulnerable and Outdated Components ) 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#2-licensing-risks] Licensing Risks 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#2-licensing-risks] 
AI development often involves diverse software and dataset licenses, creating risks if not properly managed. Different open-source and proprietary licenses impose varying legal requirements. Dataset licenses may restrict usage, distribution, or commercialization. 

3. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#3-outdated-or-deprecated-models] Outdated or Deprecated Models 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#3-outdated-or-deprecated-models] 
Using outdated or deprecated models that are no longer maintained leads to security issues. 

4. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#4-vulnerable-pre-trained-model] Vulnerable Pre-Trained Model 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#4-vulnerable-pre-trained-model] 
Models are binary black boxes and unlike open source, static inspection can offer little to security assurances. Vulnerable pre-trained models can contain hidden biases, backdoors, or other malicious features that have not been identified through the safety evaluations of model repository. Vulnerable models can be created by both poisoned datasets and direct model tampering using tehcniques such as ROME also known as lobotomisation. 

5. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#5-weak-model-provenance] Weak Model Provenance 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#5-weak-model-provenance] 
Currently there are no strong provenance assurances in published models. Model Cards and associated documentation provide model information and relied upon users, but they offer no guarantees on the origin of the model. An attacker can compromise supplier account on a model repo or create a similar one and combine it with social engineering techniques to compromise the supply-chain of an LLM application. 

6. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#6-vulnerable-lora-adapters] Vulnerable LoRA adapters 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#6-vulnerable-lora-adapters] 
LoRA is a popular fine-tuning technique that enhances modularity by allowing pre-trained layers to be bolted onto an existing LLM. The method increases efficiency but create new risks, where a malicious LorA adapter compromises the integrity and security of the pre-trained base model. This can happen both in collaborative model merge environments but also exploiting the support for LoRA from popular inference deployment platforms such as vLMM and OpenLLM where adapters can be downloaded and applied to a deployed model. 

7. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#7-exploit-collaborative-development-processes] Exploit Collaborative Development Processes 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#7-exploit-collaborative-development-processes] 
Collaborative model merge and model handling services (e.g. conversions) hosted in shared environments can be exploited to introduce vulnerabilities in shared models. Model merging is is very popular on Hugging Face with model-merged models topping the OpenLLM leaderboard and can be exploited to bypass reviews. Similarly, services such as conversation bot have been proved to be vulnerable to maniputalion and introduce malicious code in models. 

8. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#8-llm-model-on-device-supply-chain-vulnerabilities] LLM Model on Device supply-chain vulnerabilities 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#8-llm-model-on-device-supply-chain-vulnerabilities] 
LLM models on device increase the supply attack surface with compromised manufactured processes and exploitation of device OS or fimware vulnerabilities to compromise models. Attackers can reverse engineer and re-package applications with tampered models. 

9. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#9-unclear-tcs-and-data-privacy-policies] Unclear T&Cs and Data Privacy Policies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#9-unclear-tcs-and-data-privacy-policies] 
Unclear T&Cs and data privacy policies of the model operators lead to the application’s sensitive data being used for model training and subsequent sensitive information exposure. This may also apply to risks from using copyrighted material by the model supplier. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#prevention-and-mitigation-strategies] Prevention and Mitigation Strategies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#prevention-and-mitigation-strategies] 
Carefully vet data sources and suppliers, including T&Cs and their privacy policies, only using trusted suppliers. Regularly review and audit supplier Security and Access, ensuring no changes in their security posture or T&Cs. 

Understand and apply the mitigations found in the OWASP Top Ten’s “A06:2021 – Vulnerable and Outdated Components.” This includes vulnerability scanning, management, and patching components. For development environments with access to sensitive data, apply these controls in those environments, too. (Ref. link: [https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/] A06:2021 – Vulnerable and Outdated Components ) 

Apply comprehensive AI Red Teaming and Evaluations when selecting a third party model. Decoding Trust is an example of a Trustworthy AI benchmark for LLMs but models can finetuned to by pass published benchmarks. Use extensive AI Red Teaming to evaluate the model, especially in the use cases you are planning to use the model for. 

Maintain an up-to-date inventory of components using a Software Bill of Materials (SBOM) to ensure you have an up-to-date, accurate, and signed inventory, preventing tampering with deployed packages. SBOMs can be used to detect and alert for new, zero-date vulnerabilities quickly. AI BOMs and ML SBOMs are an emerging area and you should evaluate options starting with OWASP CycloneDX 

To mitigate AI licensing risks, create an inventory of all types of licenses involved using BOMs and conduct regular audits of all software, tools, and datasets, ensuring compliance and transparency through BOMs. Use automated license management tools for real-time monitoring and train teams on licensing models. Maintain detailed licensing documentation in BOMs. 

Only use models from verifiable sources and use third-party model integrity checks with signing and file hashes to compensate for the lack of strong model provenance. Similarly, use code signing for externally supplied code. 

Implement strict monitoring and auditing practices for collaborative model development environments to prevent and quickly detect any abuse. “HuggingFace SF_Convertbot Scanner” is an example of automated scripts to use. (Ref. link: [https://gist.github.com/rossja/d84a93e5c6b8dd2d4a538aa010b29163] HuggingFace SF_Convertbot Scanner ) 

AAnomaly detection and adversarial robustness tests on supplied models and data can help detect tampering and poisoning as discussed in “LLM04 Data and Model Poisoning; ideally, this should be part of MLOps and LLM pipelines; however, these are emerging techniques and may be easier to implement as part of red teaming exercises. 

Implement a patching policy to mitigate vulnerable or outdated components. Ensure the application relies on a maintained version of APIs and underlying model. 

Encrypt models deployed at AI edge with integrity checks and use vendor attestation APIs to prevent tampered apps and models and terminate applications of unrecognized firmware. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#sample-attack-scenarios] Sample Attack Scenarios 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#sample-attack-scenarios] 
Scenario #1: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-1-vulnerable-python-library] Vulnerable Python Library 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-1-vulnerable-python-library] 
An attacker exploits a vulnerable Python library to compromise an LLM app. This happened in the first Open AI data breach. Attacks on the PyPi package registry tricked model developers into downloading a compromised PyTorch dependency with malware in a model development environment. A more sophisticated example of this type of attack is Shadow Ray attack on the Ray AI framework used by many vendors to manage AI infrastructure. In this attack, five vulnerabilities are believed to have been exploited in the wild affecting many servers. 

Scenario #2: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-2-direct-tampering] Direct Tampering 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-2-direct-tampering] 
Direct Tampering and publishing a model to spread misinformation. This is an actual attack with PoisonGPT bypassing Hugging Face safety features by directly changing model parameters. 

Scenario #3: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-3-finetuning-popular-model] Finetuning Popular Model 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-3-finetuning-popular-model] 
An attacker finetunes a popular open access model to remove key safety features and perform high in a specific domain (insurance). The model is finetuned to score highly on safety benchmarks but has very targeted triggers. They deploy it on Hugging Face for victims to use it exploiting their trust on benchmark assurances. 

Scenario #4: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-4-pre-trained-models] Pre-Trained Models 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-4-pre-trained-models] 
An LLM system deploys pre-trained models from a widely used repository without thorough verification. A compromised model introduces malicious code, causing biased outputs in certain contexts and leading to harmful or manipulated outcomes 

Scenario #5: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-5-compromised-third-party-supplier] Compromised Third-Party Supplier 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-5-compromised-third-party-supplier] 
A compromised third-party supplier provides a vulnerable LorA adapter that is being merged to an LLM using model merge on Hugging Face. 

Scenario #6: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-6-supplier-infiltration] Supplier Infiltration 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-6-supplier-infiltration] 
An attacker infiltrates a third-party supplier and compromises the production of a LoRA (Low-Rank Adaptation) adapter intended for integration with an on-device LLM deployed using frameworks like vLLM or OpenLLM. The compromised LoRA adapter is subtly altered to include hidden vulnerabilities and malicious code. Once this adapter is merged with the LLM, it provides the attacker with a covert entry point into the system. The malicious code can activate during model operations, allowing the attacker to manipulate the LLM’s outputs. 

Scenario #7: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-7-cloudborne-and-cloudjacking-attacks] CloudBorne and CloudJacking Attacks 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-7-cloudborne-and-cloudjacking-attacks] 
These attacks target cloud infrastructures, leveraging shared resources and vulnerabilities in the virtualization layers. CloudBorne involves exploiting firmware vulnerabilities in shared cloud environments, compromising the physical servers hosting virtual instances. CloudJacking refers to malicious control or misuse of cloud instances, potentially leading to unauthorized access to critical LLM deployment platforms. Both attacks represent significant risks for supply chains reliant on cloud-based ML models, as compromised environments could expose sensitive data or facilitate further attacks. 

Scenario #8: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-8-leftovers-cve-2023-4969] LeftOvers (CVE-2023-4969) 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-8-leftovers-cve-2023-4969] 
LeftOvers exploitation of leaked GPU local memory to recover sensitive data. An attacker can use this attack to exfiltrate sensitive data in production servers and development workstations or laptops. 

Scenario #9: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-9-wizardlm] WizardLM 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-9-wizardlm] 
Following the removal of WizardLM, an attacker exploits the interest in this model and publish a fake version of the model with the same name but containing malware and backdoors. 

Scenario #10: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-10-model-mergeformat-conversion-service] Model Merge/Format Conversion Service 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-10-model-mergeformat-conversion-service] 
An attacker stages an attack with a model merge or format conversation service to compromise a publicly available access model to inject malware. This is an actual attack published by vendor HiddenLayer. 

Scenario #11: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-11-reverse-engineer-mobile-app] Reverse-Engineer Mobile App 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-11-reverse-engineer-mobile-app] 
An attacker reverse-engineers an mobile app to replace the model with a tampered version that leads the user to scam sites. Users are encouraged to dowload the app directly via social engineering techniques. This is a “real attack on predictive AI” that affected 116 Google Play apps including popular security and safety-critical applications used for as cash recognition, parental control, face authentication, and financial service. (Ref. link: [https://arxiv.org/abs/2006.08131] real attack on predictive AI ) 

Scenario #12: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-12-dataset-poisoning] Dataset Poisoning 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-12-dataset-poisoning] 
An attacker poisons publicly available datasets to help create a back door when fine-tuning models. The back door subtly favors certain companies in different markets. 

Scenario #13: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-13-tcs-and-privacy-policy] T&Cs and Privacy Policy 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#scenario-13-tcs-and-privacy-policy] 
An LLM operator changes its T&Cs and Privacy Policy to require an explicit opt out from using application data for model training, leading to the memorization of sensitive data. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#reference-links] Reference Links 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#reference-links] 
 [https://blog.mithrilsecurity.io/poisongpt-how-we-hid-a-lobotomized-llm-on-hugging-face-to-spread-fake-news] PoisonGPT: How we hid a lobotomized LLM on Hugging Face to spread fake news 

 [https://developers.googleblog.com/en/large-language-models-on-device-with-mediapipe-and-tensorflow-lite/] Large Language Models On-Device with MediaPipe and TensorFlow Lite 

 [https://hiddenlayer.com/research/silent-sabotage/] Hijacking Safetensors Conversion on Hugging Face 

 [https://atlas.mitre.org/techniques/AML.T0010] ML Supply Chain Compromise 

 [https://docs.vllm.ai/en/latest/models/lora.html] Using LoRA Adapters with vLLM 

 [https://arxiv.org/pdf/2311.05553] Removing RLHF Protections in GPT-4 via Fine-Tuning 

 [https://huggingface.co/blog/peft_merging] Model Merging with PEFT 

 [https://gist.github.com/rossja/d84a93e5c6b8dd2d4a538aa010b29163] HuggingFace SF_Convertbot Scanner 

 [https://www.csoonline.com/article/2075540/thousands-of-servers-hacked-due-to-insecurely-deployed-ray-ai-framework.html] Thousands of servers hacked due to insecurely deployed Ray AI framework 

 [https://blog.trailofbits.com/2024/01/16/leftoverlocals-listening-to-llm-responses-through-leaked-gpu-local-memory/] LeftoverLocals: Listening to LLM responses through leaked GPU local memory 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#related-frameworks-and-taxonomies] Related Frameworks and Taxonomies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM03_SupplyChain.md#related-frameworks-and-taxonomies] 
Refer to this section for comprehensive information, scenarios strategies relating to infrastructure deployment, applied environment controls and other best practices. 

 [https://atlas.mitre.org/techniques/AML.T0010] ML Supply Chain Compromise – MITRE ATLAS 

Share this: 

 [https://genai.owasp.org/llmrisk/llm032025-supply-chain/?share=twitter] Share on X (Opens in new window) X 

 [https://genai.owasp.org/llmrisk/llm032025-supply-chain/?share=facebook] Share on Facebook (Opens in new window) Facebook 

More 

 [https://genai.owasp.org/llmrisk/llm032025-supply-chain/#print?share=print] Print (Opens in new window) Print 

Email a link to a friend (Opens in new window) Email 

 [https://genai.owasp.org/llmrisk/llm032025-supply-chain/?share=x] Share on X (Opens in new window) X 

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
LLM03:2025 Supply Chain
