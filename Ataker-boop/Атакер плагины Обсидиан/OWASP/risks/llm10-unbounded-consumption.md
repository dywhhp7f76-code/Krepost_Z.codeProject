---
tags: [атакер, ingested]
source: https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/
---

# LLM10 Unbounded Consumption

> Источник: https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/

OWASP LLM10: 2025 Unbounded Consumption Skip to content 
LLM10:2025 Unbounded Consumption 

Unbounded Consumption refers to the process where a Large Language Model (LLM) generates outputs based on input queries or prompts. Inference is a critical function of LLMs, involving the application of learned patterns and knowledge to produce relevant responses or predictions. 

Attacks designed to disrupt service, deplete the target’s financial resources, or even steal intellectual property by cloning a model’s behavior all depend on a common class of security vulnerability in order to succeed. Unbounded Consumption occurs when a Large Language Model (LLM) application allows users to conduct excessive and uncontrolled inferences, leading to risks such as denial of service (DoS), economic losses, model theft, and service degradation. The high computational demands of LLMs, especially in cloud environments, make them vulnerable to resource exploitation and unauthorized usage. 

Common Examples of Vulnerability 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#common-examples-of-vulnerability] 
1. Variable-Length Input Flood 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#1-variable-length-input-flood] 
Attackers can overload the LLM with numerous inputs of varying lengths, exploiting processing inefficiencies. This can deplete resources and potentially render the system unresponsive, significantly impacting service availability. 

2. Denial of Wallet (DoW) 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#2-denial-of-wallet-dow] 
By initiating a high volume of operations, attackers exploit the cost-per-use model of cloud-based AI services, leading to unsustainable financial burdens on the provider and risking financial ruin. 

3. Continuous Input Overflow 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#3-continuous-input-overflow] 
Continuously sending inputs that exceed the LLM’s context window can lead to excessive computational resource use, resulting in service degradation and operational disruptions. 

4. Resource-Intensive Queries 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#4-resource-intensive-queries] 
Submitting unusually demanding queries involving complex sequences or intricate language patterns can drain system resources, leading to prolonged processing times and potential system failures. 

5. Model Extraction via API 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#5-model-extraction-via-api] 
Attackers may query the model API using carefully crafted inputs and prompt injection techniques to collect sufficient outputs to replicate a partial model or create a shadow model. This not only poses risks of intellectual property theft but also undermines the integrity of the original model. 

6. Functional Model Replication 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#6-functional-model-replication] 
Using the target model to generate synthetic training data can allow attackers to fine-tune another foundational model, creating a functional equivalent. This circumvents traditional query-based extraction methods, posing significant risks to proprietary models and technologies. 

7. Side-Channel Attacks 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#7-side-channel-attacks] 
Malicious attackers may exploit input filtering techniques of the LLM to execute side-channel attacks, harvesting model weights and architectural information. This could compromise the model’s security and lead to further exploitation. 

Prevention and Mitigation Strategies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#prevention-and-mitigation-strategies] 
1. Input Validation 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#1-input-validation] 
Implement strict input validation to ensure that inputs do not exceed reasonable size limits. 

2. Limit Exposure of Logits and Logprobs 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#2-limit-exposure-of-logits-and-logprobs] 
Restrict or obfuscate the exposure of logit_bias and logprobs in API responses. Provide only the necessary information without revealing detailed probabilities. 

3. Rate Limiting 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#3-rate-limiting] 
Apply rate limiting and user quotas to restrict the number of requests a single source entity can make in a given time period. 

4. Resource Allocation Management 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#4-resource-allocation-management] 
Monitor and manage resource allocation dynamically to prevent any single user or request from consuming excessive resources. 

5. Timeouts and Throttling 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#5-timeouts-and-throttling] 
Set timeouts and throttle processing for resource-intensive operations to prevent prolonged resource consumption. 

6.Sandbox Techniques 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#6sandbox-techniques] 
Restrict the LLM’s access to network resources, internal services, and APIs. 

This is particularly significant for all common scenarios as it encompasses insider risks and threats. Furthermore, it governs the extent of access the LLM application has to data and resources, thereby serving as a crucial control mechanism to mitigate or prevent side-channel attacks. 

7. Comprehensive Logging, Monitoring and Anomaly Detection 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#7-comprehensive-logging-monitoring-and-anomaly-detection] 
Continuously monitor resource usage and implement logging to detect and respond to unusual patterns of resource consumption. 

8. Watermarking 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#8-watermarking] 
Implement watermarking frameworks to embed and detect unauthorized use of LLM outputs. 

9. Graceful Degradation 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#9-graceful-degradation] 
Design the system to degrade gracefully under heavy load, maintaining partial functionality rather than complete failure. 

10. Limit Queued Actions and Scale Robustly 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#10-limit-queued-actions-and-scale-robustly] 
Implement restrictions on the number of queued actions and total actions, while incorporating dynamic scaling and load balancing to handle varying demands and ensure consistent system performance. 

11. Adversarial Robustness Training 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#11-adversarial-robustness-training] 
Train models to detect and mitigate adversarial queries and extraction attempts. 

12. Glitch Token Filtering 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#12-glitch-token-filtering] 
Build lists of known glitch tokens and scan output before adding it to the model’s context window. 

13. Access Controls 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#13-access-controls] 
Implement strong access controls, including role-based access control (RBAC) and the principle of least privilege, to limit unauthorized access to LLM model repositories and training environments. 

14. Centralized ML Model Inventory 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#14-centralized-ml-model-inventory] 
Use a centralized ML model inventory or registry for models used in production, ensuring proper governance and access control. 

15. Automated MLOps Deployment 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#15-automated-mlops-deployment] 
Implement automated MLOps deployment with governance, tracking, and approval workflows to tighten access and deployment controls within the infrastructure. 

Example Attack Scenarios 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#example-attack-scenarios] 
Scenario #1: Uncontrolled Input Size 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#scenario-1-uncontrolled-input-size] 
An attacker submits an unusually large input to an LLM application that processes text data, resulting in excessive memory usage and CPU load, potentially crashing the system or significantly slowing down the service. 

Scenario #2: Repeated Requests 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#scenario-2-repeated-requests] 
An attacker transmits a high volume of requests to the LLM API, causing excessive consumption of computational resources and making the service unavailable to legitimate users. 

Scenario #3: Resource-Intensive Queries 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#scenario-3-resource-intensive-queries] 
An attacker crafts specific inputs designed to trigger the LLM’s most computationally expensive processes, leading to prolonged CPU usage and potential system failure. 

Scenario #4: Denial of Wallet (DoW) 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#scenario-4-denial-of-wallet-dow] 
An attacker generates excessive operations to exploit the pay-per-use model of cloud-based AI services, causing unsustainable costs for the service provider. 

Scenario #5: Functional Model Replication 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#scenario-5-functional-model-replication] 
An attacker uses the LLM’s API to generate synthetic training data and fine-tunes another model, creating a functional equivalent and bypassing traditional model extraction limitations. 

Scenario #6: Bypassing System Input Filtering 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#scenario-6-bypassing-system-input-filtering] 
A malicious attacker bypasses input filtering techniques and preambles of the LLM to perform a side-channel attack and retrieve model information to a remote controlled resource under their control. 

Reference Links 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#reference-links] 
 [https://avidml.org/database/avid-2023-v009/] Proof Pudding (CVE-2019-20634) AVID ( moohax & monoxgas ) 

 [https://arxiv.org/abs/2403.06634] arXiv:2403.06634 Stealing Part of a Production Language Model arXiv 

 [https://www.deeplearning.ai/the-batch/how-metas-llama-nlp-model-leaked/] Runaway LLaMA | How Meta’s LLaMA NLP model leaked : Deep Learning Blog 

 [https://arxiv.org/pdf/1803.05847.pdf] I Know What You See: : Arxiv White Paper 

 [https://ieeexplore.ieee.org/document/10080996] A Comprehensive Defense Framework Against Model Extraction Attacks : IEEE 

 [https://crfm.stanford.edu/2023/03/13/alpaca.html] Alpaca: A Strong, Replicable Instruction-Following Model : Stanford Center on Research for Foundation Models (CRFM) 

 [https://www.kdnuggets.com/2023/03/watermarking-help-mitigate-potential-risks-llms.html] How Watermarking Can Help Mitigate The Potential Risks Of LLMs? : KD Nuggets 

 [https://www.rand.org/content/dam/rand/pubs/research_reports/RRA2800/RRA2849-1/RAND_RRA2849-1.pdf] Securing AI Model Weights Preventing Theft and Misuse of Frontier Models 

 [https://arxiv.org/abs/2006.03463] Sponge Examples: Energy-Latency Attacks on Neural Networks: Arxiv White Paper arXiv 

 [https://about.sourcegraph.com/blog/security-update-august-2023] Sourcegraph Security Incident on API Limits Manipulation and DoS Attack Sourcegraph 

Related Frameworks and Taxonomies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM10_UnboundedConsumption.md#related-frameworks-and-taxonomies] 
Refer to this section for comprehensive information, scenarios strategies relating to infrastructure deployment, applied environment controls and other best practices. 

 [https://cwe.mitre.org/data/definitions/400.html] MITRE CWE-400: Uncontrolled Resource Consumption MITRE Common Weakness Enumeration 

 [https://atlas.mitre.org/tactics/AML.TA0000] AML.TA0000 ML Model Access: Mitre ATLAS & [https://atlas.mitre.org/techniques/AML.T0024] AML.T0024 Exfiltration via ML Inference API MITRE ATLAS 

 [https://atlas.mitre.org/techniques/AML.T0029] AML.T0029 – Denial of ML Service MITRE ATLAS 

 [https://atlas.mitre.org/techniques/AML.T0034] AML.T0034 – Cost Harvesting MITRE ATLAS 

 [https://atlas.mitre.org/techniques/AML.T0025] AML.T0025 – Exfiltration via Cyber Means MITRE ATLAS 

 [https://owasp.org/www-project-machine-learning-security-top-10/docs/ML05_2023-Model_Theft.html] OWASP Machine Learning Security Top Ten – ML05:2023 Model Theft OWASP ML Top 10 

 [https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/] API4:2023 – Unrestricted Resource Consumption OWASP Web Application Top 10 

 [https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/] OWASP Resource Management OWASP Secure Coding Practices 

Share this: 

 [https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/?share=twitter] Share on X (Opens in new window) X 

 [https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/?share=facebook] Share on Facebook (Opens in new window) Facebook 

More 

 [https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/#print?share=print] Print (Opens in new window) Print 

Email a link to a friend (Opens in new window) Email 

 [https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/?share=x] Share on X (Opens in new window) X 

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
LLM10:2025 Unbounded Consumption
