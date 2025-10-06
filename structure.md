Aviator/
│
├── 📄 ROOT FILES
│   ├── config.py                    ✅ AŽURIRANO v5.0
│   ├── logger.py                    ✅ ZADRŽANO (ali proveri da li je v3.0)
│   ├── requirements.txt             ✅ AŽURIRANO
│   ├── README.md                    ✅ PREPISANO v5.0
│   ├── CHANGELOG.md                 ✅ NOVO
│   ├── .gitignore                   ✅ AŽURIRANO
│   ├── javascript.txt               ✅ ZADRŽANO
│   │
│   ├── setup.py                     ✅ NOVO (helper - dijagnostika)
│   ├── quick_start.py               ✅ NOVO (helper - wizard)
│   │
│   ├── main.py                      ❌ OBRIŠI (zastareo)
│   └── __init__.py                  ✅ ZADRŽANO
│
├── 📁 apps/                         ✨ PROGRAMI
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── base_app.py                  ✅ NOVO (template za sve programe)
│   │
│   ├── main_data_collector.py      ✅ NOVO (Program 1)
│   ├── rgb_collector.py             ✅ NOVO (Program 2)
│   ├── betting_agent.py             ✅ PRERAĐENO (Program 3)
│   │
│   ├── data_collector.py            ❌ OBRIŠI (zamenjen sa main_data_collector.py)
│   └── prediction_improved.py       ❓ PROVERI (ako se ne koristi → obriši)
│
├── 📁 core/                         🔧 OSNOVNA LOGIKA
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── coord_manager.py             ✅ PRERAĐENO v5.0
│   ├── screen_reader.py             ✅ ZADRŽANO
│   ├── ocr_processor.py             ✅ ZADRŽANO
│   ├── gui_controller.py            ✅ ZADRŽANO
│   ├── bookmaker_process.py         ⚠️  MOŽDA ZASTAREO (proveri)
│   ├── bookmaker_orchestrator.py    ⚠️  MOŽDA ZASTAREO (proveri)
│   └── coord_getter.py              ⚠️  MOŽDA ZASTAREO (coord editor to radi)
│
├── 📁 regions/                      👁️ SCREEN REGION HANDLERS
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── base_region.py               ✅ ZADRŽANO
│   ├── score.py                     ✅ ZADRŽANO
│   ├── my_money.py                  ✅ ZADRŽANO
│   ├── other_count.py               ✅ ZADRŽANO
│   ├── other_money.py               ✅ ZADRŽANO
│   └── game_phase.py                ✅ ZADRŽANO
│
├── 📁 database/                     💾 DATABASE LAYER
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── models.py                    ✅ PRERAĐENO v5.0
│   ├── setup.py                     ⚠️  MOŽDA ZASTAREO (models.py to radi)
│   ├── database.py                  ⚠️  MOŽDA ZASTAREO
│   ├── writer.py                    ⚠️  MOŽDA ZASTAREO
│   ├── worker.py                    ⚠️  MOŽDA ZASTAREO
│   └── optimizer.py                 ✅ ZADRŽANO (možda koristan)
│
├── 📁 utils/                        🛠️ UTILITIES
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── region_visualizer.py         ✅ PRERAĐENO v2.0
│   ├── region_editor.py             ✅ ZADRŽANO (ali možda treba update)
│   ├── coordinate_migrator.py       ✅ NOVO (jednokratna upotreba)
│   │
│   ├── diagnostic.py                ⚠️  DUPLIKAT sa setup.py?
│   ├── data_analyzer.py             ✅ ZADRŽANO (korisno)
│   ├── debug_monitor.py             ✅ ZADRŽANO (korisno)
│   └── performance_analyzer.py      ✅ ZADRŽANO (korisno)
│
├── 📁 ai/                           🤖 MACHINE LEARNING
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── color_collector.py           ⚠️  DUPLIKAT sa rgb_collector.py?
│   ├── color_selector.py            ✅ ZADRŽANO (za labeling)
│   ├── model_trainer.py             ✅ ZADRŽANO (za treniranje)
│   └── phase_predictor.py           ✅ ZADRŽANO (za predikcije)
│
├── 📁 tests/                        🧪 TESTING
│   ├── __init__.py                  ✅ ZADRŽANO
│   ├── quick_check.py               ✅ ZADRŽANO
│   ├── test_betting.py              ✅ ZADRŽANO
│   ├── test_ocr_accuracy.py         ✅ ZADRŽANO
│   ├── test_reader.py               ✅ ZADRŽANO
│   └── screenshots/                 📸 Ovde idu region verification slike
│
├── 📁 data/                         📦 DATA STORAGE
│   ├── coordinates/
│   │   └── bookmaker_coords.json    ✅ NOVA STRUKTURA v5.0
│   │
│   ├── databases/
│   │   ├── main_game_data.db        ✅ NOVA BAZA
│   │   ├── rgb_training_data.db     ✅ NOVA BAZA
│   │   ├── betting_history.db       ✅ NOVA BAZA
│   │   ├── aviator.db               ⚠️  STARA BAZA (možda obrisati)
│   │   └── game_phase.db            ⚠️  STARA BAZA (možda obrisati)
│   │
│   └── models/
│       ├── game_phase_kmeans.pkl    ✅ ZADRŽANO
│       ├── bet_button_kmeans.pkl    ✅ ZADRŽANO
│       └── *.pkl                    ✅ Ostali ML modeli
│
└── 📁 logs/                         📝 LOG FILES
    ├── main_data_collector.log      ✅ NOVI LOG
    ├── rgb_collector.log            ✅ NOVI LOG
    ├── betting_agent.log            ✅ NOVI LOG
    ├── main.log                     ⚠️  STARI LOG (možda obrisati)
    └── error.log                    ✅ ZADRŽANO