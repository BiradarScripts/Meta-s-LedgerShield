# LedgerShield v2 Mini-Blog / 2-Minute Video Script

LedgerShield v2 asks a different question from most fraud benchmarks:

not “can an agent spot a suspicious invoice?”

but “can an agent operate a defensible enterprise control regime?”

The environment is set inside enterprise accounts-payable workflows. Agents investigate invoices, vendor histories, email threads, bank changes, and delayed callback artifacts. They work under budget and step limits, and they are graded against hidden backend state rather than exposed scaffold metrics.

The public benchmark now runs in blind mode by default. That matters because it prevents agents from overfitting to evaluator internals like SPRT state, reward-machine progress, or tool-ranking scaffolds. Diagnostics are still available, but they are explicitly separated from benchmark runs.

LedgerShield v2 also exposes three official tracks.

Case Track measures single-case control behavior.
Portfolio Track measures AP-week performance with institutional memory and finite review capacity.
Adversarial Data Track measures resistance to deceptive content inside documents, email threads, and tool outputs.

The headline metrics changed too. We do not hide safety behavior inside one average score. LedgerShield now reports control-satisfied resolution, institutional utility, unsafe release rate, certificate validity, and explicit result classes like valid success, correct but policy incomplete, and unsafe release.

Finally, generalization is mechanism-aware. Holdout and contrastive suites are defined by hidden mechanism tuples like attack family, compromise channel, pressure profile, and control weakness, so agents are tested on control logic rather than surface memorization.

That is the core idea behind LedgerShield v2:

make the benchmark stricter, clearer, and harder to game, while keeping it grounded in real enterprise payment integrity work.
