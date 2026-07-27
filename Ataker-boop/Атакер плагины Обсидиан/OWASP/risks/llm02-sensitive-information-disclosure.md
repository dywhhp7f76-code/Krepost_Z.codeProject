---
tags: [атакер, ingested]
source: https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/
---

# LLM02 Sensitive Information Disclosure

> Источник: https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/

LLM02:2025 Sensitive Information Disclosure - OWASP Gen AI Security Project Skip to content 
LLM02:2025 Sensitive Information Disclosure 

Sensitive information can affect both the LLM and its application context. This includes personal identifiable information (PII), financial details, health records, confidential business data, security credentials, and legal documents. Proprietary models may also have unique training methods and source code considered sensitive, especially in closed or foundation models. 

LLMs, especially when embedded in applications, risk exposing sensitive data, proprietary algorithms, or confidential details through their output. This can result in unauthorized data access, privacy violations, and intellectual property breaches. Consumers should be aware of how to interact safely with LLMs. They need to understand the risks of unintentionally providing sensitive data, which may later be disclosed in the model’s output. 

To reduce this risk, LLM applications should perform adequate data sanitization to prevent user data from entering the training model. Application owners should also provide clear Terms of Use policies, allowing users to opt out of having their data included in the training model. Adding restrictions within the system prompt about data types that the LLM should return can provide mitigation against sensitive information disclosure. However, such restrictions may not always be honored and could be bypassed via prompt injection or other methods. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#common-examples-of-vulnerability] Common Examples of Vulnerability 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#common-examples-of-vulnerability] 
1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-pii-leakage] PII Leakage 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-pii-leakage] 
Personal identifiable information (PII) may be disclosed during interactions with the LLM. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-proprietary-algorithm-exposure] Proprietary Algorithm Exposure 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-proprietary-algorithm-exposure] 
Poorly configured model outputs can reveal proprietary algorithms or data. Revealing training data can expose models to inversion attacks, where attackers extract sensitive information or reconstruct inputs. For instance, as demonstrated in the ‘Proof Pudding’ attack (CVE-2019-20634), disclosed training data facilitated model extraction and inversion, allowing attackers to circumvent security controls in machine learning algorithms and bypass email filters. 

3. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#3-sensitive-business-data-disclosure] Sensitive Business Data Disclosure 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#3-sensitive-business-data-disclosure] 
Generated responses might inadvertently include confidential business information. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#prevention-and-mitigation-strategies] Prevention and Mitigation Strategies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#prevention-and-mitigation-strategies] 
###@ Sanitization: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-integrate-data-sanitization-techniques] Integrate Data Sanitization Techniques 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-integrate-data-sanitization-techniques] 
Implement data sanitization to prevent user data from entering the training model. This includes scrubbing or masking sensitive content before it is used in training. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-robust-input-validation] Robust Input Validation 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-robust-input-validation] 
Apply strict input validation methods to detect and filter out potentially harmful or sensitive data inputs, ensuring they do not compromise the model. 

###@ Access Controls: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-enforce-strict-access-controls] Enforce Strict Access Controls 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-enforce-strict-access-controls] 
Limit access to sensitive data based on the principle of least privilege. Only grant access to data that is necessary for the specific user or process. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-restrict-data-sources] Restrict Data Sources 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-restrict-data-sources] 
Limit model access to external data sources, and ensure runtime data orchestration is securely managed to avoid unintended data leakage. 

###@ Federated Learning and Privacy Techniques: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-utilize-federated-learning] Utilize Federated Learning 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-utilize-federated-learning] 
Train models using decentralized data stored across multiple servers or devices. This approach minimizes the need for centralized data collection and reduces exposure risks. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-incorporate-differential-privacy] Incorporate Differential Privacy 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-incorporate-differential-privacy] 
Apply techniques that add noise to the data or outputs, making it difficult for attackers to reverse-engineer individual data points. 

###@ User Education and Transparency: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-educate-users-on-safe-llm-usage] Educate Users on Safe LLM Usage 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-educate-users-on-safe-llm-usage] 
Provide guidance on avoiding the input of sensitive information. Offer training on best practices for interacting with LLMs securely. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-ensure-transparency-in-data-usage] Ensure Transparency in Data Usage 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-ensure-transparency-in-data-usage] 
Maintain clear policies about data retention, usage, and deletion. Allow users to opt out of having their data included in training processes. 

###@ Secure System Configuration: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-conceal-system-preamble] Conceal System Preamble 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-conceal-system-preamble] 
Limit the ability for users to override or access the system’s initial settings, reducing the risk of exposure to internal configurations. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-reference-security-misconfiguration-best-practices] Reference Security Misconfiguration Best Practices 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-reference-security-misconfiguration-best-practices] 
Follow guidelines like “OWASP API8:2023 Security Misconfiguration” to prevent leaking sensitive information through error messages or configuration details. (Ref. link: [https://owasp.org/API-Security/editions/2023/en/0xa8-security-misconfiguration/] OWASP API8:2023 Security Misconfiguration ) 

###@ Advanced Techniques: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-homomorphic-encryption] Homomorphic Encryption 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#1-homomorphic-encryption] 
Use homomorphic encryption to enable secure data analysis and privacy-preserving machine learning. This ensures data remains confidential while being processed by the model. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-tokenization-and-redaction] Tokenization and Redaction 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#2-tokenization-and-redaction] 
Implement tokenization to preprocess and sanitize sensitive information. Techniques like pattern matching can detect and redact confidential content before processing. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#example-attack-scenarios] Example Attack Scenarios 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#example-attack-scenarios] 
Scenario #1: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#scenario-1-unintentional-data-exposure] Unintentional Data Exposure 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#scenario-1-unintentional-data-exposure] 
A user receives a response containing another user’s personal data due to inadequate data sanitization. 

Scenario #2: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#scenario-2-targeted-prompt-injection] Targeted Prompt Injection 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#scenario-2-targeted-prompt-injection] 
An attacker bypasses input filters to extract sensitive information. 

Scenario #3: [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#scenario-3-data-leak-via-training-data] Data Leak via Training Data 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#scenario-3-data-leak-via-training-data] 
Negligent data inclusion in training leads to sensitive information disclosure. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#reference-links] Reference Links 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#reference-links] 
 [https://cybernews.com/security/chatgpt-samsung-leak-explained-lessons/] Lessons learned from ChatGPT’s Samsung leak : Cybernews 

 [https://www.foxbusiness.com/politics/ai-data-leak-crisis-prevent-company-secrets-chatgpt] AI data leak crisis: New tool prevents company secrets from being fed to ChatGPT : Fox Business 

 [https://www.wired.com/story/chatgpt-poem-forever-security-roundup/] ChatGPT Spit Out Sensitive Data When Told to Repeat ‘Poem’ Forever : Wired 

 [https://neptune.ai/blog/using-differential-privacy-to-build-secure-models-tools-methods-best-practices] Using Differential Privacy to Build Secure Models : Neptune Blog 

 [https://avidml.org/database/avid-2023-v009/] Proof Pudding (CVE-2019-20634) AVID ( moohax & monoxgas ) 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#related-frameworks-and-taxonomies] Related Frameworks and Taxonomies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM02_SensitiveInformationDisclosure.md#related-frameworks-and-taxonomies] 
Refer to this section for comprehensive information, scenarios strategies relating to infrastructure deployment, applied environment controls and other best practices. 

 [https://atlas.mitre.org/techniques/AML.T0024.000] AML.T0024.000 – Infer Training Data Membership MITRE ATLAS 

 [https://atlas.mitre.org/techniques/AML.T0024.001] AML.T0024.001 – Invert ML Model MITRE ATLAS 

 [https://atlas.mitre.org/techniques/AML.T0024.002] AML.T0024.002 – Extract ML Model MITRE ATLAS 

Share this: 

 [https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/?share=twitter] Share on X (Opens in new window) X 

 [https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/?share=facebook] Share on Facebook (Opens in new window) Facebook 

More 

 [https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/#print?share=print] Print (Opens in new window) Print 

Email a link to a friend (Opens in new window) Email 

 [https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/?share=x] Share on X (Opens in new window) X 

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
LLM02:2025 Sensitive Information Disclosure
