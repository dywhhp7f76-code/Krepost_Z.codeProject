---
tags: [атакер, ingested]
source: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/
---

# LLM06 Excessive Agency

> Источник: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/

LLM06:2025 Excessive Agency - OWASP Gen AI Security Project Skip to content 
LLM06:2025 Excessive Agency 

An LLM-based system is often granted a degree of agency by its developer – the ability to call functions or interface with other systems via extensions (sometimes referred to as tools, skills or plugins by different vendors) to undertake actions in response to a prompt. The decision over which extension to invoke may also be delegated to an LLM ‘agent’ to dynamically determine based on input prompt or LLM output. Agent-based systems will typically make repeated calls to an LLM using output from previous invocations to ground and direct subsequent invocations. 

Excessive Agency is the vulnerability that enables damaging actions to be performed in response to unexpected, ambiguous or manipulated outputs from an LLM, regardless of what is causing the LLM to malfunction. Common triggers include: 

hallucination/confabulation caused by poorly-engineered benign prompts, or just a poorly-performing model; 

direct/indirect prompt injection from a malicious user, an earlier invocation of a malicious/compromised extension, or (in multi-agent/collaborative systems) a malicious/compromised peer agent. 

The root cause of Excessive Agency is typically one or more of: 

excessive functionality; 

excessive permissions; 

excessive autonomy. 

Excessive Agency can lead to a broad range of impacts across the confidentiality, integrity and availability spectrum, and is dependent on which systems an LLM-based app is able to interact with. 

Note: Excessive Agency differs from Insecure Output Handling which is concerned with insufficient scrutiny of LLM outputs. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#common-examples-of-risks] Common Examples of Risks 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#common-examples-of-risks] 
1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#1-excessive-functionality] Excessive Functionality 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#1-excessive-functionality] 
An LLM agent has access to extensions which include functions that are not needed for the intended operation of the system. For example, a developer needs to grant an LLM agent the ability to read documents from a repository, but the 3rd-party extension they choose to use also includes the ability to modify and delete documents. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#2-excessive-functionality] Excessive Functionality 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#2-excessive-functionality] 
An extension may have been trialled during a development phase and dropped in favor of a better alternative, but the original plugin remains available to the LLM agent. 

3. Excessive Functionality 

An LLM plugin with open-ended functionality fails to properly filter the input instructions for commands outside what’s necessary for the intended operation of the application. E.g., an extension to run one specific shell command fails to properly prevent other shell commands from being executed. 

4. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#4-excessive-permissions] Excessive Permissions 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#4-excessive-permissions] 
An LLM extension has permissions on downstream systems that are not needed for the intended operation of the application. E.g., an extension intended to read data connects to a database server using an identity that not only has SELECT permissions, but also UPDATE, INSERT and DELETE permissions. 

5. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#5-excessive-permissions] Excessive Permissions 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#5-excessive-permissions] 
An LLM extension that is designed to perform operations in the context of an individual user accesses downstream systems with a generic high-privileged identity. E.g., an extension to read the current user’s document store connects to the document repository with a privileged account that has access to files belonging to all users. 

6. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#6-excessive-autonomy] Excessive Autonomy 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#6-excessive-autonomy] 
An LLM-based application or extension fails to independently verify and approve high-impact actions. E.g., an extension that allows a user’s documents to be deleted performs deletions without any confirmation from the user. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#prevention-and-mitigation-strategies] Prevention and Mitigation Strategies 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#prevention-and-mitigation-strategies] 
The following actions can prevent Excessive Agency: 

1. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#1-minimize-extensions] Minimize extensions 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#1-minimize-extensions] 
Limit the extensions that LLM agents are allowed to call to only the minimum necessary. For example, if an LLM-based system does not require the ability to fetch the contents of a URL then such an extension should not be offered to the LLM agent. 

2. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#2-minimize-extension-functionality] Minimize extension functionality 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#2-minimize-extension-functionality] 
Limit the functions that are implemented in LLM extensions to the minimum necessary. For example, an extension that accesses a user’s mailbox to summarise emails may only require the ability to read emails, so the extension should not contain other functionality such as deleting or sending messages. 

3. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#3-avoid-open-ended-extensions] Avoid open-ended extensions 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#3-avoid-open-ended-extensions] 
Avoid the use of open-ended extensions where possible (e.g., run a shell command, fetch a URL, etc.) and use extensions with more granular functionality. For example, an LLM-based app may need to write some output to a file. If this were implemented using an extension to run a shell function then the scope for undesirable actions is very large (any other shell command could be executed). A more secure alternative would be to build a specific file-writing extension that only implements that specific functionality. 

4. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#4-minimize-extension-permissions] Minimize extension permissions 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#4-minimize-extension-permissions] 
Limit the permissions that LLM extensions are granted to other systems to the minimum necessary in order to limit the scope of undesirable actions. For example, an LLM agent that uses a product database in order to make purchase recommendations to a customer might only need read access to a ‘products’ table; it should not have access to other tables, nor the ability to insert, update or delete records. This should be enforced by applying appropriate database permissions for the identity that the LLM extension uses to connect to the database. 

5. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#5-execute-extensions-in-users-context] Execute extensions in user’s context 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#5-execute-extensions-in-users-context] 
Track user authorization and security scope to ensure actions taken on behalf of a user are executed on downstream systems in the context of that specific user, and with the minimum privileges necessary. For example, an LLM extension that reads a user’s code repo should require the user to authenticate via OAuth and with the minimum scope required. 

6. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#6-require-user-approval] Require user approval 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#6-require-user-approval] 
Utilise human-in-the-loop control to require a human to approve high-impact actions before they are taken. This may be implemented in a downstream system (outside the scope of the LLM application) or within the LLM extension itself. For example, an LLM-based app that creates and posts social media content on behalf of a user should include a user approval routine within the extension that implements the ‘post’ operation. 

7. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#7-complete-mediation] Complete mediation 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#7-complete-mediation] 
Implement authorization in downstream systems rather than relying on an LLM to decide if an action is allowed or not. Enforce the complete mediation principle so that all requests made to downstream systems via extensions are validated against security policies. 

8. [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#8-sanitise-llm-inputs-and-outputs] Sanitise LLM inputs and outputs 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#8-sanitise-llm-inputs-and-outputs] 
Follow secure coding best practice, such as applying OWASP’s recommendations in ASVS (Application Security Verification Standard), with a particularly strong focus on input sanitisation. Use Static Application Security Testing (SAST) and Dynamic and Interactive application testing (DAST, IAST) in development pipelines. 

The following options will not prevent Excessive Agency, but can limit the level of damage caused: 

Log and monitor the activity of LLM extensions and downstream systems to identify where undesirable actions are taking place, and respond accordingly. 

Implement rate-limiting to reduce the number of undesirable actions that can take place within a given time period, increasing the opportunity to discover undesirable actions through monitoring before significant damage can occur. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#example-attack-scenarios] Example Attack Scenarios 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#example-attack-scenarios] 
An LLM-based personal assistant app is granted access to an individual’s mailbox via an extension in order to summarise the content of incoming emails. To achieve this functionality, the extension requires the ability to read messages, however the plugin that the system developer has chosen to use also contains functions for sending messages. Additionally, the app is vulnerable to an indirect prompt injection attack, whereby a maliciously-crafted incoming email tricks the LLM into commanding the agent to scan the user’s inbox for senitive information and forward it to the attacker’s email address. This could be avoided by: 

eliminating excessive functionality by using an extension that only implements mail-reading capabilities, 

eliminating excessive permissions by authenticating to the user’s email service via an OAuth session with a read-only scope, and/or 

eliminating excessive autonomy by requiring the user to manually review and hit ‘send’ on every mail drafted by the LLM extension. 

Alternatively, the damage caused could be reduced by implementing rate limiting on the mail-sending interface. 

 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#reference-links] Reference Links 
 [https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md#reference-links] 
 [https://promptarmor.substack.com/p/slack-ai-data-exfiltration-from-private] Slack AI data exfil from private channels : PromptArmor 

 [https://www.twilio.com/en-us/blog/rogue-ai-agents-secure-your-apis] Rogue Agents: Stop AI From Misusing Your APIs : Twilio 

 [https://embracethered.com/blog/posts/2023/chatgpt-cross-plugin-request-forgery-and-prompt-injection./] Embrace the Red: Confused Deputy Problem : Embrace The Red 

 [https://github.com/NVIDIA/NeMo-Guardrails/blob/main/docs/security/guidelines.md] NeMo-Guardrails: Interface guidelines : NVIDIA Github 

 [https://simonwillison.net/2023/Apr/25/dual-llm-pattern/] Simon Willison: Dual LLM Pattern : Simon Willison 

Share this: 

 [https://genai.owasp.org/llmrisk/llm062025-excessive-agency/?share=twitter] Share on X (Opens in new window) X 

 [https://genai.owasp.org/llmrisk/llm062025-excessive-agency/?share=facebook] Share on Facebook (Opens in new window) Facebook 

More 

 [https://genai.owasp.org/llmrisk/llm062025-excessive-agency/#print?share=print] Print (Opens in new window) Print 

Email a link to a friend (Opens in new window) Email 

 [https://genai.owasp.org/llmrisk/llm062025-excessive-agency/?share=x] Share on X (Opens in new window) X 

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
LLM06:2025 Excessive Agency
