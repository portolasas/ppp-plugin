# Testing prompts

- The test hub of Prompt Builder takes a CSV with the input columns and `TestCaseExpectedOutput`, several rows; keep it as `TESTS.csv` next to the prompt. [B][V]
- Test chat and `Execute Agent and wait` do not suit long inputs: the limit was about 2,000 characters. Test long inputs through the flow or the test hub. [B][V]
- Keep a small regression set (e.g. 20 confirmed cases of a classifier) and run it again before every publish; names in test rows anonymised. [B]
- Before writing test data for a model output check that the prompt names a positive trigger for it, that schema and route allow the output, and that the process allows it in this phase. If one is missing, invent no test data; clarify the gap (ppp-clarify) [O] (GEN-20260927-MAC-01).
