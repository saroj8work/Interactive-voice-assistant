# Aura Interactive ELN: Life Sciences Domain Knowledge & UI Action Catalog

## 1. Electronic Lab Notebook (ELN) System & Overview
The **Aura Interactive ELN** is a secure, 21 CFR Part 11-compliant digital laboratory workspace designed for biotechnology, pharmaceutical research, chemical biology, and academic laboratories. It integrates real-time scientific note-taking, molecular structure modeling, inventory tracking, equipment scheduling, and autonomous AI-assisted operations.

---

## 2. Autonomous Web UI Actions & Navigation Catalog
When a user speaks or requests operations in the web application, the assistant issues structured `ui_actions` that the frontend executes autonomously without requiring human clicks or manual typing.

### Supported UI Action Directives
* **`OPEN_MODAL`**: Opens specified dialogs, drawers, and laboratory utilities.
  * Targets:
    * `inventory`: Opens the chemical reagents and biological inventory manager.
    * `equipment`: Opens the equipment booking calendar and maintenance schedule.
    * `chemical_search`: Opens the chemical structure search modal (search by SMILES, formula, or mass).
    * `barcode_scanner`: Opens the camera-based 1D barcode and 2D DataMatrix/QR sample scanner.
    * `formal_report`: Opens the formal GLP/GMP laboratory report generator and exporter.
    * `tasks`: Opens the protocol task checklist and milestone tracker.
    * `templates`: Opens the protocol templates library (PCR, Western Blot, Cell Passage).
    * `locations`: Opens freezer management and 9x9 / 10x10 cryogenic storage box grids.
    * `history`: Opens entry revision history, visual diffs, and audit trail verifications.
* **`CLOSE_MODAL`**: Closes the currently active modal or drawer.
* **`SET_THEME`**: Switches application visual theme.
  * Target: `dark` (Default cyberpunk scientific dark mode) or `light` (Clean high-contrast laboratory daylight mode).
* **`TOGGLE_SIDEBAR`**: Expands or collapses the project tree navigation sidebar.
* **`SWITCH_EDITOR_MODE`**:
  * Target: `edit` (Markdown editing with molecule/stoichiometry embeds) or `preview` (Publication-grade rendered view).
* **`SEARCH`**: Opens global search and executes a search query across all experiments and samples.
* **`NOTIFY`**: Displays a laboratory toast notification banner with custom text and type (`info`, `success`, `error`).

---

## 3. Life Sciences & Molecular Biology Knowledge Base

### 3.1. Polymerase Chain Reaction (PCR) Standards
* **Reaction Mix (50 µL typical volume)**:
  * 10 µL 5X Reaction Buffer
  * 1 µL 10 mM dNTP Mix (final 200 µM each)
  * 2.5 µL Forward Primer (10 µM stock, final 0.5 µM)
  * 2.5 µL Reverse Primer (10 µM stock, final 0.5 µM)
  * 1–50 ng Plasmid DNA or 50–250 ng Genomic DNA template
  * 0.5 µL High-Fidelity DNA Polymerase (e.g. Q5, Phusion, Taq)
  * Nuclease-free water up to 50.0 µL
* **Thermocycling Protocol**:
  1. Initial Denaturation: 98°C for 30–60 seconds (hot start activation).
  2. 25–35 Cycles of:
     * Denaturation: 98°C for 10 seconds.
     * Annealing: 55–68°C (typically $T_m - 3^\circ\text{C}$ to $T_m + 3^\circ\text{C}$) for 20 seconds.
     * Extension: 72°C for 30 seconds per kilobase (kb) of amplicon.
  3. Final Extension: 72°C for 2–5 minutes.
  4. Final Hold: 4°C indefinitely.

### 3.2. Agarose Gel Electrophoresis
* **Gel Concentration Guidelines**:
  * 0.7% Agarose: Optimal for large fragments (5 kb – 10 kb).
  * 1.0% Agarose: Standard resolution for general DNA fragments (500 bp – 5 kb).
  * 1.5%–2.0% Agarose: High resolution for small amplicons (100 bp – 1 kb).
* **Running Buffer**: 1X TAE (Tris-Acetate-EDTA) or 1X TBE (Tris-Borate-EDTA).
* **Staining**: GelRed, SYBR Safe, or Ethidium Bromide (0.5 µg/mL).
* **Running Conditions**: 90–120 Volts for 45–60 minutes.

### 3.3. Spectrophotometry & Nucleic Acid Purity Standards
* **DNA Quantification ($A_{260}$)**: 1 OD unit at 260 nm = 50 µg/mL double-stranded DNA.
* **RNA Quantification ($A_{260}$)**: 1 OD unit at 260 nm = 40 µg/mL single-stranded RNA.
* **$A_{260}/A_{280}$ Ratio**:
  * Pure DNA: 1.80 ± 0.05. Ratios < 1.6 indicate residual protein or phenol contamination.
  * Pure RNA: 2.00 ± 0.05.
* **$A_{260}/A_{230}$ Ratio**: Expected 2.0–2.2. Lower values indicate contamination with chaotropic salts (EDTA, carbohydrates, guanidine thiocyanate).

### 3.4. Western Blot & Protein Analysis
* **Lysis**: RIPA Buffer with protease and phosphatase inhibitor cocktails at 4°C.
* **SDS-PAGE**: 4–20% gradient Tris-Glycine or Bis-Tris gel run at 120V.
* **Transfer**: Wet or semi-dry transfer onto 0.2 µm / 0.45 µm PVDF membrane (pre-wetted with 100% methanol) or Nitrocellulose membrane.
* **Blocking**: 5% Non-fat dry milk or 5% Bovine Serum Albumin (BSA) in TBST (Tris-buffered saline with 0.1% Tween-20) for 1 hour at room temperature.
* **Primary Antibody**: Diluted in blocking buffer (typically 1:1000), incubated overnight at 4°C with gentle rocking.
* **Secondary Antibody**: HRP-conjugated secondary (1:5000), 1 hour at room temperature, followed by Enhanced Chemiluminescence (ECL) detection.

---

## 4. Stoichiometry, Dilution, & Chemical Calculations

### 4.1. The Standard Dilution Formula ($C_1 V_1 = C_2 V_2$)
* $C_1$: Concentration of stock solution.
* $V_1$: Volume of stock solution to pipette.
* $C_2$: Target desired concentration.
* $V_2$: Target final total volume.
* Required Diluent Volume = $V_2 - V_1$.

### 4.2. Molarity & Mass Formula
$$\text{Mass (grams)} = \text{Molarity (mol/L)} \times \text{Volume (L)} \times \text{Molecular Weight (g/mol)}$$

### 4.3. Standard Biological Buffers Preparation
* **PBS (Phosphate-Buffered Saline) 1X, pH 7.4**:
  * 137 mM NaCl (8.0 g/L)
  * 2.7 mM KCl (0.2 g/L)
  * 10 mM $\text{Na}_2\text{HPO}_4$ (1.42 g/L)
  * 1.8 mM $\text{KH}_2\text{PO}_4$ (0.24 g/L)
  * Adjust pH to 7.4 with HCl/NaOH, autoclave at 121°C for 20 minutes.
* **TE Buffer 1X, pH 8.0**:
  * 10 mM Tris-HCl (pH 8.0)
  * 1 mM EDTA (pH 8.0)
* **Tris-Glycine SDS Running Buffer 1X**:
  * 25 mM Tris Base
  * 192 mM Glycine
  * 0.1% (w/v) SDS

---

## 5. Cell Culture & Biobanking Protocols
* **Incubator Standards**: 37.0°C, 5.0% $\text{CO}_2$, >90% relative humidity.
* **Aseptic Technique**: Perform all cell manipulation inside Class II Type A2 Biosafety Cabinets. Spray all items with 70% isopropanol/ethanol prior to entry.
* **Passaging**: Wash with sterile PBS ($-\text{Ca}^{2+}/-\text{Mg}^{2+}$), treat with 0.05% or 0.25% Trypsin-EDTA for 2–5 minutes at 37°C. Neutralize with complete serum-containing growth media.
* **Cryopreservation**: Freezing medium composed of 90% Fetal Bovine Serum (FBS) + 10% Dimethyl Sulfoxide (DMSO). Cool at -1°C/minute in a controlled-rate isopropanol container (Mr. Frosty) to -80°C, then transfer to liquid nitrogen vapor phase (-196°C).

---

## 6. Regulatory Compliance & Quality Standards (GLP / GMP / 21 CFR Part 11)
* **Audit Trail Immutability**: Every record update, deletion attempt, and revision creates an unalterable timestamped ledger entry recording user ID, IP address, timestamp, and previous vs. new values.
* **Electronic Signatures**: A signature certifies that the signer has reviewed the scientific findings. Signatures require re-authentication and state the meaning of signature (e.g. "Author", "Technical Reviewer", "QA Approval").
* **Sample Custody Lineage**: All sample transfers between researchers, storage locations (-80°C Freezers, LN2 tanks), or clinical trial sites must log a formal Chain of Custody record.
