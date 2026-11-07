# ASSAY reference library

Every entry carries a **verification key**:

- **[V]** — source opened and confirmed during the 2026-11-07 research pass
  that built this program (models, pricing, kernels, papers);
- **[C]** — canonical classic, carried from the predecessor program's
  review-vetted bibliography (TRACEGUARD docs/REFERENCES.md; original
  records vetted by its multi-POV reviews);
- **[R]** — repo-vetted by the predecessor program (not re-opened here).

Never a memory-only citation. Additions after any freeze are append-only.

---

## 1. Attacks (implemented methods)

1. **[V]** Zou, A., Wang, Z., Carlini, N., et al. *Universal and Transferable Adversarial Attacks on Aligned Language Models (GCG).* arXiv:2307.15043, 2023. https://arxiv.org/abs/2307.15043
2. **[V]** Wei, A., Haghtalab, N., Steinhardt, J. *Jailbroken: How Does LLM Safety Training Fail?* NeurIPS 2023. https://arxiv.org/abs/2307.02483
3. **[V]** Chao, P., Robey, A., Dobriban, E., et al. *Jailbreaking Black Box Large Language Models in Twenty Queries (PAIR).* arXiv:2310.08419, 2023. https://arxiv.org/abs/2310.08419
4. **[V]** Mehrotra, A., Zampetakis, M., Kassianik, P., et al. *Tree of Attacks: Jailbreaking Black-Box LLMs Automatically (TAP).* NeurIPS 2024. https://arxiv.org/abs/2312.02119
5. **[V]** Russinovich, M., Salem, A., Eldan, R. *Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack.* USENIX Security 2025. https://arxiv.org/abs/2404.01833
6. **[V]** Li, X., Zhou, Z., Zhu, J., et al. *DeepInception: Hypnotize Large Language Model to Be Jailbreaker.* arXiv:2311.03191, 2023. https://arxiv.org/abs/2311.03191
7. **[V]** Handa, D., Zhang, Z., Saeidi, A., et al. *When "Competency" in Reasoning Opens the Door to Vulnerability: Jailbreaking LLMs via Novel Complex Ciphers.* arXiv:2402.10601, 2024. https://arxiv.org/abs/2402.10601
8. **[V]** Jin, H., Zhou, A., Menke, J.D., et al. *Jailbreaking Large Language Models Against Moderation Guardrails via Cipher Characters.* arXiv:2405.20413, 2024. https://arxiv.org/abs/2405.20413
9. **[V]** Zeng, Y., Lin, H., Zhang, J., et al. *How Johnny Can Persuade LLMs to Jailbreak Them (PAP).* ACL 2024 Long. https://arxiv.org/abs/2401.06373
10. **[V]** Vega, J., Huang, J., Zhang, G., et al. *Stochastic Monkeys at Play: Random Augmentations Cheaply Break LLM Safety Alignment.* arXiv:2411.02785, 2024. https://arxiv.org/abs/2411.02785
11. **[R]** Anthropic. *Many-shot Jailbreaking.* 2024. https://www.anthropic.com/research/many-shot-jailbreaking
12. **[V]** Zhu, Z., Zhang, H., Wang, R., et al. *To Think or Not to Think: Exploring the Unthinking Vulnerability in Large Reasoning Models.* arXiv:2502.12202, 2025. https://arxiv.org/abs/2502.12202
13. **[V]** Brůna, L., Bridges, R., Ek, A. *Prefilling the Reasoning Channel: Output-Prefix Attacks on Reasoning LLMs.* arXiv:2609.29775, 2026. https://arxiv.org/abs/2609.29775
14. **[V]** Dou, Y., Yang, W. *AJAR: Adaptive Jailbreak Architecture for Red-teaming.* arXiv:2601.10971, 2026. https://arxiv.org/abs/2601.10971
15. **[V]** Deng, Y., Zhang, W., Pan, S.J., et al. *Multilingual Jailbreak Challenges in Large Language Models (MultiJail).* ICLR 2024. https://arxiv.org/abs/2310.06474

## 2. Measurement-validity critiques (the RQ1 motivation)

16. **[V]** Souly, A., Lu, Q., Bowen, D., et al. *A StrongREJECT for Empty Jailbreaks.* NeurIPS 2024 D&B. https://arxiv.org/abs/2402.10260
17. **[V]** Davis, L., Emil-Popescu, R., Jana, S. *Did the LLM Answer the Question? A Semantic Reconstruction Game for Jailbreak Evaluation.* arXiv:2610.19306, 2026. https://arxiv.org/abs/2610.19306
18. **[V]** Maple, C., Kumar, A., Tapwal, R. *Single-Configuration Attack Success Rate Is Not Enough: Jailbreak Evaluations Should Report Distributional Attack Success.* arXiv:2605.09070, 2026. https://arxiv.org/abs/2605.09070
19. **[V]** Wu, Q., Wadhwa, S., Mohanty, P., et al. *Validity-Aware Jailbreak Evaluation for Large Language Models (SEAV).* EMNLP 2026. https://arxiv.org/abs/2609.00498
20. **[V]** Yan, Y., Sun, S., Wang, Z., et al. *Confusion is the Final Barrier: Rethinking Jailbreak Evaluation.* arXiv:2508.16347, 2025. https://arxiv.org/abs/2508.16347
21. **[V]** Jebraeeli, V., Romero, J., Wang, Y., et al. *Policy Is Not Capability: Some Safety Benchmarks Measure Which Definition of "Unsafe" You Trained On.* NeurIPS 2026 TAE workshop. https://arxiv.org/abs/2610.25060
22. **[V]** Deckenbach, K., Puerto, H., Geiping, J., et al. *Models That Know How Evaluations Are Designed Score Safer.* arXiv:2605.28591, 2026. https://arxiv.org/abs/2605.28591
23. **[V]** Zhu, D., Wang, Z., Bao, X., et al. *Jailbroken Frontier Models Retain Their Capabilities.* arXiv:2605.00267, 2026. https://arxiv.org/abs/2605.00267

## 3. Benchmarks and guard models

24. **[V]** Mazeika, M., Phan, L., Yin, X., et al. *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal.* ICML 2024. https://arxiv.org/abs/2402.04249
25. **[V]** Chao, P., Debenedetti, E., Robey, A., et al. *JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models.* NeurIPS 2024 D&B. https://arxiv.org/abs/2404.01318
26. **[V]** Röttger, P., Kirk, H.R., Vidgen, B., et al. *XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models.* NAACL 2024 Main. https://arxiv.org/abs/2308.01263
27. **[V]** Inan, H., Upasani, K., Chi, J., et al. *Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations.* arXiv:2312.06674, 2023. https://arxiv.org/abs/2312.06674
28. **[V]** Zeng, W., Liu, Y., Mullins, R., et al. *ShieldGemma: Generative AI Content Moderation Based on Gemma.* arXiv:2407.21772, 2024. https://arxiv.org/abs/2407.21772
29. **[V]** Han, S., Rao, K., Ettinger, A., et al. *WildGuard: Open One-Stop Moderation Tools for Safety Risks, Jailbreaks, and Refusals of LLMs.* NeurIPS 2024. https://arxiv.org/abs/2406.18495

## 4. LLM-judge reliability

30. **[V]** Zheng, L., Chiang, W., Sheng, Y., et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023 D&B. https://arxiv.org/abs/2306.05685
31. **[V]** Wang, P., Li, L., Chen, L., et al. *Large Language Models are not Fair Evaluators.* ACL 2024 Long. https://aclanthology.org/2024.acl-long.511/
32. **[V]** Panickssery, A., Bowman, S.R., Feng, S. *LLM Evaluators Recognize and Favor Their Own Generations.* NeurIPS 2024. https://arxiv.org/abs/2404.13076
33. **[V]** Tan, S., Zhuang, S., Montgomery, K., et al. *JudgeBench: A Benchmark for Evaluating LLM-based Judges.* ICLR 2025. https://arxiv.org/abs/2410.12784
34. **[V]** Zhou, Y., Ye, W., Liu, Y., et al. *Style Over Substance: Content-Invariant Wrappers Flip LLM Safety-Judge Verdicts.* arXiv:2609.08236, 2026. https://arxiv.org/abs/2609.08236
35. **[V]** Li, X., Huang, A., Zhang, M., et al. *Same Attack, Different Judge.* arXiv:2610.17820, 2026. https://arxiv.org/abs/2610.17820

## 5. Mechanistic refusal and steering (RQ3)

36. **[V]** Arditi, A., Obeso, O., Syed, A., et al. *Refusal in Language Models Is Mediated by a Single Direction.* NeurIPS 2024 main. https://arxiv.org/abs/2406.11717
37. **[V]** Panickssery, N., Gabrieli, N., Schulz, J., et al. *Steering Llama 2 via Contrastive Activation Addition (CAA).* ACL 2024 Long. https://arxiv.org/abs/2312.06681
38. **[V]** Turner, A.M., Thiergart, L., Leech, G., et al. *Steering Language Models With Activation Engineering (ActAdd).* arXiv:2308.10248, 2023. https://arxiv.org/abs/2308.10248
39. **[V]** Zou, A., Phan, L., Chen, S., et al. *Representation Engineering: A Top-Down Approach to AI Transparency (RepE).* arXiv:2310.01405, 2023. https://arxiv.org/abs/2310.01405
40. **[V]** Bullwinkel, B., Russinovich, M., Salem, A., et al. *A Representation Engineering Perspective on the Effectiveness of Multi-Turn Jailbreaks.* arXiv:2507.02956, 2025. https://arxiv.org/abs/2507.02956
41. **[V]** Lin, Y., He, P., Xu, H., et al. *Towards Understanding Jailbreak Attacks in LLMs: A Representation Space Analysis.* EMNLP 2024 Main. https://arxiv.org/abs/2406.10794
42. **[V]** Cao, Z., Yang, Y., Zhao, H. *SCANS: Mitigating the Exaggerated Safety for LLMs via Safety-Conscious Activation Steering.* AAAI 2025. https://arxiv.org/abs/2408.11491
43. **[V]** Korznikov, A., Galichin, A., Dontsov, A., et al. *The Rogue Scalpel: Activation Steering Compromises LLM Safety.* arXiv:2509.22067, 2025. https://arxiv.org/abs/2509.22067
44. **[V]** Evseev, G., Solodkin, V., Bylinkin, D., et al. *WRDO: Weighted Refusal Direction Optimization in Aligned Language Models.* EMNLP 2026. https://arxiv.org/abs/2610.29555
45. **[V]** Ivanova, A. *Is Refusal Direction Universal across Low-Resourced Languages?* BlackboxNLP@EMNLP 2026. https://arxiv.org/abs/2610.28897

## 6. Reasoning-model safety

46. **[V]** Zhou, K., Liu, C., Zhao, X., et al. *The Hidden Risks of Large Reasoning Models: A Safety Assessment of R1.* arXiv:2502.12659, 2025. https://arxiv.org/abs/2502.12659
47. **[V]** Baker, B., Huizinga, J., Gao, L., et al. *Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation.* arXiv:2503.11926, 2025. https://arxiv.org/abs/2503.11926
48. **[V]** Chen, Y., Benton, J., Radhakrishnan, A., et al. *Reasoning Models Don't Always Say What They Think.* arXiv:2505.05410, 2025. https://arxiv.org/abs/2505.05410
49. **[V]** Huang, T., Hu, S., Ilhan, F., et al. *Safety Tax: Safety Alignment Makes Your Large Reasoning Models Less Reasonable.* arXiv:2503.00555, 2025. https://arxiv.org/abs/2503.00555
50. **[V]** Needham, J., Edkins, G., Pimpale, G., et al. *Large Language Models Often Know When They Are Being Evaluated.* arXiv:2505.23836, 2025. https://arxiv.org/abs/2505.23836
51. **[V]** Zeng, Q., Xuan, W., Cui, L., et al. *Thinking Out Loud: Do Reasoning Models Know When They're Right?* EMNLP 2025. https://arxiv.org/abs/2504.06564
52. **[V]** Yang, Y., Yu, H., Wang, Y., et al. *First Token Matters: Understanding Safety Collapse in Large Reasoning Models.* CICAI 2026. https://arxiv.org/abs/2609.18471

## 7. Agentic safety and control (context)

53. **[R]** Korbak, T., Balesni, M., Barnes, E., et al. *Chain of Thought Monitorability: A New and Fragile Opportunity for AI Safety.* arXiv:2507.11473, 2025. https://arxiv.org/abs/2507.11473
54. **[R]** Greenblatt, R., Shlegeris, B., Sachan, K., et al. *AI Control: Improving Safety Despite Intentional Subversion.* ICML 2024. https://arxiv.org/abs/2312.06942
55. **[V]** Denison, C., MacDiarmid, M., Barez, F., et al. *Sycophancy to Subterfuge: Investigating Reward-Tampering in Language Models.* arXiv:2406.10162, 2024. https://arxiv.org/abs/2406.10162
56. **[V]** Anthropic. *Agentic misalignment: LLMs as insider threats.* 2025. https://www.anthropic.com/research/agentic-misalignment
57. **[V]** Meinke, A., Schoen, B., Scheurer, J., et al. *Frontier Models are Capable of In-context Scheming.* arXiv:2412.04984, 2024. https://arxiv.org/abs/2412.04984
58. **[V]** Kutasov, J., et al. (METR). *SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents.* arXiv:2506.15740, 2025. https://arxiv.org/abs/2506.15740
59. **[V]** DeepSeek-AI. *DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL.* Nature 645:633-638, 2025. https://arxiv.org/abs/2501.12948

## 8. Multilingual safety

60. **[V]** Shen, L., Tan, W., Chen, S., et al. *The Language Barrier: Dissecting Safety Challenges of LLMs in Multilingual Contexts.* Findings of ACL 2024. https://arxiv.org/abs/2401.13136
61. **[V]** Mondal, S., Mamta, Varshney, D., et al. *IndicSafeEval: Safety Robustness of LLMs under Multilingual Persuasive Jailbreak Attacks.* Findings of EMNLP 2026. https://arxiv.org/abs/2609.03781
62. **[V]** Marx, D., Dunaiski, M. *Multilingual jailbreaking of LLMs using low-resource languages.* arXiv:2605.18239, 2026. https://arxiv.org/abs/2605.18239

## 9. Contamination and benchmark integrity

63. **[V]** Sainz, O., Campos, J.A., García-Ferrero, I., et al. *NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmark.* Findings of EMNLP 2024. https://arxiv.org/abs/2310.18018
64. **[V]** Palavalli, M., Bertsch, A., Gormley, M.R. *A Taxonomy for Data Contamination in Large Language Models.* CONDA @ ACL 2024. https://arxiv.org/abs/2407.08716
65. **[V]** Dong, Y., Jiang, X., Liu, H., et al. *Generalization or Memorization: Data Contamination and Trustworthy Evaluation for LLMs.* ACL 2024. https://arxiv.org/abs/2402.15938
66. **[V]** Tao, Y., Wang, T., Dong, Y., et al. *Detecting Data Contamination from RL Post-training for LLMs.* ICLR 2026. https://arxiv.org/abs/2510.09259
67. **[V]** Zhang, J., Elgohary, A., Wang, X., et al. *Jailbreak Distillation: Renewable Safety Benchmarking.* arXiv:2505.22037, 2025. https://arxiv.org/abs/2505.22037

## 10. Statistical methodology

68. **[C]** Efron, B. *Bootstrap Methods: Another Look at the Jackknife.* Annals of Statistics 7(1), 1979.
69. **[C]** Efron, B., Tibshirani, R. *An Introduction to the Bootstrap.* Chapman & Hall/CRC, 1993.
70. **[C]** Field, C.A., Welsh, A.H. *Bootstrapping Clustered Data.* JRSS-B 69(3), 2007.
71. **[C]** Cameron, A.C., Miller, D.L. *A Practitioner's Guide to Cluster-Robust Inference.* Journal of Human Resources 50(2), 2015.
72. **[C]** Holm, S. *A Simple Sequentially Rejective Multiple Test Procedure.* Scandinavian Journal of Statistics 6(2), 1979.
73. **[C]** Benjamini, Y., Hochberg, Y. *Controlling the False Discovery Rate.* JRSS-B 57(1), 1995.
74. **[C]** Schuirmann, D.J. *A Comparison of the Two One-Sided Tests Procedure…* Journal of Pharmacokinetics and Biopharmaceutics 15(6), 1987.
75. **[C]** Lakens, D. *Equivalence Tests: A Practical Primer.* SPPS 8(4), 2017.
76. **[C]** McNemar, Q. *Note on the Sampling Error of the Difference Between Correlated Proportions.* Psychometrika 12(2), 1947.
77. **[C]** Wilson, E.B. *Probable Inference…* JASA 22(158), 1927.
78. **[C]** Clopper, C.J., Pearson, E.S. *The Use of Confidence or Fiducial Limits…* Biometrika 26(4), 1934.
79. **[C]** Cohen, J. *A Coefficient of Agreement for Nominal Scales.* EPM 20(1), 1960.
80. **[C]** Hayes, A.F., Krippendorff, K. *Answering the Call for a Standard Reliability Measure for Coding Data.* CMM 1(1), 2007.
81. **[C]** Brier, G.W. *Verification of Forecasts Expressed in Terms of Probability.* Monthly Weather Review 78(1), 1950.
82. **[C]** Vickers, A.J., Elkin, E.B. *Decision Curve Analysis: A Novel Method for Evaluating Prediction Models.* MDM 26(6), 2006.
83. **[C]** DeLong, E.R., DeLong, D.M., Clarke-Pearson, D.L. *Comparing the Areas under Two or More Correlated ROC Curves.* Biometrics 44(3), 1988.
84. **[C]** Card, D., Henderson, P., Khandelwal, U., et al. *With Little Power Comes Great Responsibility.* EMNLP 2020. https://arxiv.org/abs/2010.06595
85. **[C]** Bouthillier, X., et al. *Accounting for Variance in Machine Learning Benchmarks.* MLSys 2021.
86. **[C]** Nosek, B.A., et al. *The Preregistration Revolution.* PNAS 115(11), 2018.
87. **[C]** Gelman, A., Loken, E. *The Statistical Crisis in Science.* American Scientist 102(6), 2014.
88. **[C]** Kerr, N.L. *HARKing.* PSPR 2(3), 1998.

## 11. Frontier safety frameworks (verified 2026-11-07)

89. **[V]** OpenAI. *Preparedness Framework, Version 2.* Apr 15, 2025. https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf
90. **[V]** Anthropic. *Responsible Scaling Policy v3.4* (effective Jul 8, 2026). https://www.anthropic.com/responsible-scaling-policy
91. **[V]** Google DeepMind. *Frontier Safety Framework v3.0.* Sep 22, 2025. https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/strengthening-our-frontier-safety-framework/frontier-safety-framework_3.pdf
92. **[V]** Anthropic. *Constitutional Classifiers.* Feb 3, 2025. https://www.anthropic.com/research/constitutional-classifiers
93. **[V]** OpenAI Alignment. *Open Sourcing Monitorability Evaluations.* Apr 23, 2026. https://alignment.openai.com/monitorability-evals/
94. **[V]** Microsoft. *AI Red Teaming Agent in Foundry (public preview).* Nov 25, 2025. https://devblogs.microsoft.com/foundry/assess-agentic-risks-with-the-ai-red-teaming-agent-in-microsoft-foundry/
95. **[V]** Meta. *Llama Guard 4* (HF model card). Apr 2025. https://huggingface.co/meta-llama/Llama-Guard-4-12B
96. **[V]** NIST. *AI Risk Management Framework 1.0.* NIST AI 100-1, 2023. https://www.nist.gov/itl/ai-risk-management-framework

## 12. Serving systems and kernels (verified 2026-11-07)

97. **[V]** Kwon, W., Li, Z., Zhuang, S., et al. *Efficient Memory Management for LLM Serving with PagedAttention (vLLM).* SOSP 2023. https://arxiv.org/abs/2309.06180
98. **[V]** vLLM project. *vLLM v0.33.0 release line.* Nov 2026. https://github.com/vllm-project/vllm/releases
99. **[V]** Zheng, L., et al. *SGLang: Efficient Execution of Structured Language Model Programs.* arXiv:2312.07104 (RadixAttention). https://arxiv.org/abs/2312.07104
100. **[V]** SGLang project. *SGLang v0.5.23.* Nov 2026. https://github.com/sgl-project/sglang/releases
101. **[V]** Dao, T., Fu, D., Ermon, S., et al. *FlashAttention.* NeurIPS 2022. https://arxiv.org/abs/2205.14135
102. **[V]** Dao, T. *FlashAttention-2.* ICLR 2024. https://arxiv.org/abs/2307.08691
103. **[V]** Shah, J., Bikshandi, G., Zhang, Y., et al. *FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision (Hopper).* arXiv:2407.08608, 2024. https://arxiv.org/abs/2407.08608
104. **[V]** FlashInfer project. v0.7.3, Nov 2026. https://github.com/flashinfer-ai/flashinfer
105. **[V]** DeepSeek-AI. *FlashMLA* (MLA kernels; Hopper path pinned at ba89a346 after the 2026-09-30 SM100/Ascend release). https://github.com/deepseek-ai/FlashMLA
106. **[V]** DeepSeek-AI. *DeepGEMM* (FP8/FP4/BF16 GEMMs, JIT via DeepJIT). https://github.com/deepseek-ai/DeepGEMM
107. **[V]** DeepSeek-AI. *DeepEP* (MoE expert-parallel communication). https://github.com/deepseek-ai/DeepEP
108. **[V]** DeepSeek-AI. *3FS* (distributed FS; KVCache path). https://github.com/deepseek-ai/3FS
109. **[V]** DeepSeek-AI. *DualPipe*; *EPLB*; *smallpond*; *DeepJIT*; *DeepSpec* (DSpark/DFlash draft models); *DeepSelect*; *TileKernels*; *Engram*; *open-infra-index* (Open-Source Week + 2026 additions). https://github.com/deepseek-ai/open-infra-index
110. **[V]** Micikevicius, P., et al. *FP8 Formats for Deep Learning.* arXiv:2209.05433, 2022. https://arxiv.org/abs/2209.05433

## 13. Model reports and pricing sources (verified 2026-11-07)

111. **[V]** Anthropic. *Claude models & pricing.* https://platform.claude.com/docs/en/about-claude/pricing
112. **[V]** Google. *Gemini API models & pricing.* https://ai.google.dev/gemini-api/docs/pricing
113. **[V]** Microsoft. *Foundry Models sold by Azure (OpenAI line)* + Azure OpenAI pricing. https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models — https://azure.microsoft.com/en-us/pricing/details/azure-openai/ (openai.com blocked in the research environment; first-party re-verified at probe time)
114. **[V]** xAI. *Grok models & pricing.* https://docs.x.ai/developers/models
115. **[V]** DeepSeek. *API pricing.* https://api-docs.deepseek.com/quick_start/pricing
116. **[V]** OpenAI. *gpt-oss-120b / gpt-oss-20b* (Apache-2.0, MXFP4). https://huggingface.co/openai/gpt-oss-120b
117. **[V]** Hugging Face model records for every open-weight matrix entry
     (DeepSeek V3.1/R1-0528/V3.2/V4-Flash/V4.1-Flash-1017; Qwen3.5/3.8;
     GLM-4.5/-Air-FP8/4.7-Flash/5; Kimi K2.5/K3.1-Pro; Llama-4
     Scout/Maverick-FP8; Mistral Large-3/Small-3.1/Ministral-3; MiniMax-M3;
     Hunyuan-A13B; LongCat-Flash-FP8; Nemotron-3.5; gemma-4) — URLs in
     `src/assay/registry/models.py`, one `Verification` record per entry.
118. **[V]** AWS. *p4de.24xlarge pricing* (8x A100-80GB; $27.447/hr on-demand us-east-1). https://instances.vantage.sh/aws/ec2/p4de.24xlarge — p5.48xlarge is region-priced and stays OUT of the price table until verified at launch (never invented).

---

### Notes on use

- Sections 1–9 ground the science; 10 the statistics; 11 the governance
  context; 12 the serving standard; 13 the matrix and cost planning.
- Pricing entries are point-in-time: re-verify at probe time and update
  the registry (fresh `verified_at`), never edit history.
- Anything not verifiable stays out — the list is honest by construction.
