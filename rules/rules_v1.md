# Rules for SWE-Agent (learned from failed traces)

Extracted by LLM agents comparing failed vs passing attempts on real GitHub issues.
Each rule addresses a concrete failure pattern observed in the data.

---

### Rule 1: UNSAFE_VARIABLE_ACCESS
When a variable's existence depends on loop execution, check if it exists (e.g. `'var' in locals()`) before referencing it, rather than pre-initializing it. Pre-initialization can alter loop semantics and mask the real issue.

_Source: `INM-6__python-odmltables-120` (11/48 passed). Failed attempts pre-initialized or checked in wrong location; passing attempt added a safe membership check at point of use._

### Rule 2: INCOMPLETE_FIX
When changing a method call (e.g. from public `.serialize()` to protected `._serialize()`), ensure you update BOTH the method name AND the argument signature to match. Changing only one produces a patch that looks correct but silently passes wrong values.

_Source: `adamboche__python-marshmallow-union-33` (63/69 passed). Failed attempts changed either the method name or the arguments, but not both together._

### Rule 3: MISSING_ERROR_HANDLING
Before accessing a dictionary or dataset element by key, always check if the key exists using a membership test or wrap in try/except. Don't assume keys exist just because related keys do.

_Source: `blairconrad__dicognito-158` (29/42 passed). Failed attempts changed variable names or bit-shift logic; passing attempt added a membership check and try/except for missing keys._

### Rule 4: INDEX_MISMATCH
When building index-dependent lists that will be accessed by `enumerate` position, ensure ALL iterations append an entry (even placeholder values like 0) to maintain length parity with the source collection. Skipping iterations creates off-by-one index errors.

_Source: `d3dave__cough-3` (12/42 passed). Failed attempts ignored the index sync problem; passing attempt appended 0 for uninitialized sections to keep lists aligned._

### Rule 5: WRONG_ABSTRACTION_LEVEL
Implement identity checks and short-circuits at the public API entry point, BEFORE any caching, database, or external service calls. Don't push the optimization down to lower abstraction layers where it's too late.

_Source: `django-money__django-money-689` (51/76 passed). Failed attempts modified backend `get_rates()` at lower layers; passing attempt added the check in the public `get_rate()` function._

### Rule 6: WRONG_PLACEMENT
When adding setup operations (like creating directories), place them BEFORE the code that depends on them, not after. Verify the order of operations: extract path, create directory, write file.

_Source: `ebmdatalab__datalab-pandas-29` (40/94 passed). Failed attempts placed directory creation after the write call, inside wrong conditional blocks, or only raised errors instead of fixing._

### Rule 7: WRONG_DIAGNOSIS
Read error messages precisely. "'NoneType' object is not subscriptable" means a value IS None, not that a key is missing. Check `value is not None` rather than `key in dict`. Match your fix to the actual error, not what you assume the error means.

_Source: `iterative__dvc-8554` (2/46 passed). All three failed attempts checked key existence; passing attempt checked if the value was not None._

### Rule 8: INDEX_MISALIGNMENT
When creating a boolean Series for DataFrame indexing with `.loc`, ensure the Series has the SAME index as the DataFrame. A boolean Series without a matching index causes silent misalignment during boolean indexing.

_Source: `mie-lab__trackintel-408` (57/69 passed). Failed attempts switched to iloc or converted index to bool; passing attempt simply added `index=sp.index` to the Series constructor._

### Rule 9: SEMANTICS_ERROR
When data cannot be converted to the required type (e.g. "N/A" to int), skip the iteration silently with `continue`. Don't warn unnecessarily or substitute misleading default values like 0 that misrepresent the actual state.

_Source: `pytorch__ignite-1044` (9/34 passed). Failed attempts added warnings or substituted 0; passing attempt silently continued, preserving absence of data._

### Rule 10: INCOMPLETE_CLEANUP
After removing a deprecated constant, variable, or feature, search the ENTIRE codebase for all usages of that name. Remove the definition, the usage code, AND the associated tests. Deleting only the definition leaves broken references.

_Source: `repobee__repobee-457` (6/15 passed). Failed attempts only deleted the constant; passing attempt also removed fallback logic in config.py and the deprecated test case._

---

Total: 10 unique rules from 10 traces
Method: LLM subagents reading full failed vs passing trajectories
