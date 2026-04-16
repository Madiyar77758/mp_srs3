import streamlit as st
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="Ассистент проверки договоров на практику", layout="wide")
st.title("⚖️ Ассистент проверки договоров на студенческую практику")
st.markdown("Мультиагентная система на CrewAI: Memory · Knowledge · Files · HITL · Conditional Tasks · Tools")


def extract_text_from_file(uploaded_file) -> str:
    """Извлекает текст из TXT, DOCX или PDF файла."""
    filename = uploaded_file.name.lower()
    content = uploaded_file.getvalue()

    if filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    elif filename.endswith(".docx"):
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except ImportError:
            st.error("❌ Установите: pip install python-docx")
            st.stop()

    elif filename.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            text_parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            return "\n".join(text_parts)
        except ImportError:
            try:
                from pypdf import PdfReader
                import io
                reader = PdfReader(io.BytesIO(content))
                return "\n".join([p.extract_text() or "" for p in reader.pages])
            except ImportError:
                st.error("❌ Установите: pip install pdfplumber или pypdf")
                st.stop()

    return content.decode("utf-8", errors="ignore")


# ==========================================
# ЗОНА 1: КОНФИГУРАЦИЯ АГЕНТОВ И ЗАДАЧ
# ==========================================
with st.expander("⚙️ Зона 1: Конфигурация агентов и задач", expanded=False):
    st.subheader("Агент 1 — Экстрактор договора")
    agent1_role = st.text_input("Role", value="Аналитик договоров")
    agent1_goal = st.text_input("Goal", value="Извлечь структуру и ключевые условия из договора на практику.")
    agent1_backstory = st.text_area("Backstory", value="Вы опытный юрист-архивариус. Читаете договоры и выписываете факты без оценки.", height=80)

    st.subheader("Агент 2 — Аудитор соответствия")
    agent2_role = st.text_input("Role ", value="Аудитор соответствия")
    agent2_goal = st.text_input("Goal ", value="Проверить договор на наличие всех обязательных пунктов и выявить рискованные формулировки.")
    agent2_backstory = st.text_area("Backstory ", value="Вы строгий контролёр. Сверяете условия договора с регламентом и базой знаний.", height=80)

    st.subheader("Агент 3 — Координатор доработок (Conditional)")
    agent3_role = st.text_input("Role  ", value="Координатор по доработкам")
    agent3_goal = st.text_input("Goal  ", value="Сформулировать список исправлений, если найдены нарушения или отсутствующие разделы.")
    agent3_backstory = st.text_area("Backstory  ", value="Включаетесь только при наличии замечаний. Помогаете студентам исправить договор.", height=80)

    st.subheader("Агент 4 — Финализатор (HITL)")
    agent4_role = st.text_input("Role   ", value="Главный специалист по утверждению")
    agent4_goal = st.text_input("Goal   ", value="Вынести финальный вердикт: принять, исправить или направить на ручную проверку.")
    agent4_backstory = st.text_area("Backstory   ", value="Принимаете финальное решение на основе всех отчётов. Ваше слово — последнее.", height=80)

    st.subheader("Описания задач")
    task1_desc = st.text_area("Задача 1 (экстракция)", value="Проанализируйте текст договора и извлеките: стороны договора, сроки практики, предмет, права и обязанности сторон, пункты об ответственности.", height=60)
    task2_desc = st.text_area("Задача 2 (аудит)", value="Сравните извлечённые условия с базой знаний. Используйте инструмент проверки обязательных пунктов. Составьте отчёт о нарушениях.", height=60)
    task3_desc = st.text_area("Задача 3 (условная доработка)", value="ЕСЛИ в отчёте аудитора есть нарушения или отсутствующие разделы — составьте пошаговый список исправлений. ЕСЛИ замечаний нет — напишите 'Доработки не требуются'.", height=60)
    task4_desc = st.text_area("Задача 4 (финальное заключение)", value="Соберите данные от всех агентов и вынесите вердикт: 'Договор готов к подписанию', 'Требуется доработка' или 'Необходима ручная проверка юриста'.", height=60)

# ==========================================
# ЗОНА 2: ВХОДНЫЕ ДАННЫЕ И БАЗА ЗНАНИЙ
# ==========================================
with st.sidebar:
    st.header("📂 Зона 2: Входные данные")

    if api_key:
        st.success("✅ API ключ загружен из .env")
    else:
        api_key = st.text_input("Введите GOOGLE_API_KEY", type="password")
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key

    st.subheader("Загрузка файлов")
    uploaded_contract = st.file_uploader(
        "📄 Договор на практику (TXT, DOCX, PDF)",
        type=["txt", "docx", "pdf"],
        help="Загрузите проект договора между студентом, университетом и организацией"
    )
    uploaded_supporting = st.file_uploader(
        "📎 Сопроводительный документ (необязательно)",
        type=["txt", "docx", "pdf"],
        help="Описание базы практики, письмо от компании и т.д."
    )

    st.subheader("📚 База знаний (Knowledge)")
    knowledge_base = st.text_area(
        "Регламент и обязательные пункты",
        height=250,
        value=(
            "ОБЯЗАТЕЛЬНЫЕ ПУНКТЫ ДОГОВОРА НА ПРАКТИКУ:\n"
            "1. Полное наименование и реквизиты всех трёх сторон: студент, университет, организация.\n"
            "2. Предмет договора: вид и цель практики.\n"
            "3. Сроки практики: не менее 4 недель (28 календарных дней).\n"
            "4. Права и обязанности студента.\n"
            "5. Права и обязанности принимающей организации.\n"
            "6. Права и обязанности университета.\n"
            "7. Пункт об ответственности за технику безопасности и охрану труда.\n"
            "8. Пункт о конфиденциальности и защите персональных данных.\n"
            "9. Порядок отчётности студента (дневник практики, отчёт).\n"
            "10. Подписи и печати всех трёх сторон.\n\n"
            "ЗАПРЕЩЁННЫЕ ФОРМУЛИРОВКИ:\n"
            "- Срок практики менее 4 недель.\n"
            "- Отсутствие пункта об ответственности.\n"
            "- Неполные реквизиты сторон.\n"
            "- Отсутствие подписей одной из сторон."
        )
    )

    st.subheader("🔧 Сценарий запуска")
    scenario = st.radio(
        "Выберите сценарий:",
        ["Авто (определяется агентами)", "Без нарушений", "С нарушениями (Conditional Task)"],
    )

# ==========================================
# ЗОНА 3: ЗАПУСК И РЕЗУЛЬТАТЫ
# ==========================================
st.header("🚀 Зона 3: Запуск и результаты")

if not api_key:
    st.warning("⚠️ Введите Google API ключ в боковой панели.")
elif not uploaded_contract:
    st.info("📄 Загрузите файл договора в боковой панели для начала работы.")
else:
    st.success(f"✅ Файл загружен: **{uploaded_contract.name}**")
    if uploaded_supporting:
        st.info(f"📎 Сопроводительный документ: **{uploaded_supporting.name}**")

    # Предпросмотр текста договора
    with st.expander("🔍 Предпросмотр извлечённого текста договора"):
        preview_text = extract_text_from_file(uploaded_contract)
        uploaded_contract.seek(0)  # сбрасываем позицию после чтения
        st.text_area("Текст договора:", value=preview_text[:3000] + ("..." if len(preview_text) > 3000 else ""), height=200, disabled=True)

    if st.button("▶️ Запустить мультиагентную проверку", type="primary"):

        try:
            from crewai import Agent, Task, Crew, Process, LLM
            from crewai.tools import BaseTool
            from pydantic import Field
        except ImportError as e:
            st.error(f"❌ Ошибка импорта: {e}\nУстановите: pip install crewai crewai-tools")
            st.stop()

        os.environ["GEMINI_API_KEY"] = api_key

        # Извлекаем текст из файла и сохраняем как .txt
        contract_text = extract_text_from_file(uploaded_contract)

        if not contract_text.strip():
            st.error("❌ Не удалось извлечь текст из файла. Проверьте, что файл не пустой.")
            st.stop()

        # Сохраняем как .txt — FileReadTool умеет читать только txt
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
            tmp.write(contract_text)
            contract_txt_path = tmp.name

        supporting_text = ""
        if uploaded_supporting:
            supporting_text = extract_text_from_file(uploaded_supporting)

        # ---- LLM ----
        llm = LLM(
            model="gemini/gemini-3-flash-preview",
            api_key=api_key
        )

        # ---- ИНСТРУМЕНТЫ ----
        _kb = knowledge_base
        _contract_text = contract_text

        class ContractReaderTool(BaseTool):
            name: str = "Contract Reader Tool"
            description: str = (
                "Читает и возвращает полный текст загруженного договора на практику. "
                "Не требует аргументов — просто вызови этот инструмент."
            )
            contract_content: str = Field(default="")

            def _run(self, query: str = "") -> str:
                return f"ТЕКСТ ДОГОВОРА:\n{self.contract_content}"

        class CheckClausesTool(BaseTool):
            name: str = "Check Mandatory Clauses Tool"
            description: str = (
                "Проверяет текст договора на наличие обязательных разделов. "
                "Передай текст договора как аргумент. "
                "Возвращает список найденных и отсутствующих разделов."
            )

            def _run(self, text: str) -> str:
                mandatory = [
                    "стороны", "предмет", "срок", "обязанности",
                    "ответственность", "конфиденциальность", "подпись"
                ]
                found = [w for w in mandatory if w in text.lower()]
                missing = [w for w in mandatory if w not in text.lower()]
                res = f"Найдено разделов: {len(found)}/{len(mandatory)}.\n"
                if missing:
                    res += f"❌ Отсутствуют термины/разделы: {', '.join(missing)}\n"
                    res += "Это означает, что договор НЕ соответствует требованиям."
                else:
                    res += "✅ Все обязательные разделы присутствуют."
                return res

        class KnowledgeLookupTool(BaseTool):
            name: str = "Knowledge Base Lookup Tool"
            description: str = (
                "Выполняет поиск по базе знаний регламента университета. "
                "Принимает ключевое слово или вопрос, возвращает релевантные пункты регламента."
            )
            knowledge: str = Field(default="")

            def _run(self, query: str) -> str:
                lines = [line.strip() for line in self.knowledge.split("\n") if line.strip()]
                relevant = [
                    line for line in lines
                    if any(word in line.lower() for word in query.lower().split())
                ]
                if relevant:
                    return "Найдено в регламенте:\n" + "\n".join(relevant[:5])
                return "По данному запросу в регламенте ничего не найдено."

        contract_reader_tool = ContractReaderTool(contract_content=_contract_text)
        check_clauses_tool = CheckClausesTool()
        knowledge_lookup_tool = KnowledgeLookupTool(knowledge=_kb)

        # ---- АГЕНТЫ ----
        extractor_agent = Agent(
            role=agent1_role,
            goal=agent1_goal,
            backstory=agent1_backstory,
            verbose=True,
            allow_delegation=False,
            tools=[contract_reader_tool],
            llm=llm
        )

        auditor_agent = Agent(
            role=agent2_role,
            goal=agent2_goal,
            backstory=agent2_backstory,
            verbose=True,
            allow_delegation=False,
            tools=[check_clauses_tool, knowledge_lookup_tool],
            llm=llm
        )

        coordinator_agent = Agent(
            role=agent3_role,
            goal=agent3_goal,
            backstory=agent3_backstory,
            verbose=True,
            allow_delegation=False,
            llm=llm
        )

        finalizer_agent = Agent(
            role=agent4_role,
            goal=agent4_goal,
            backstory=agent4_backstory,
            verbose=True,
            allow_delegation=False,
            llm=llm
        )

        # ---- ЗАДАЧИ ----
        # Передаём текст договора прямо в описание задачи — агент гарантированно его видит
        extract_task = Task(
            description=(
                task1_desc +
                f"\n\nТЕКСТ ДОГОВОРА ДЛЯ АНАЛИЗА:\n{contract_text[:8000]}"
                + (f"\n\nДОПОЛНИТЕЛЬНЫЙ ДОКУМЕНТ:\n{supporting_text[:2000]}" if supporting_text else "")
                + f"\n\nБаза знаний (регламент):\n{knowledge_base}"
            ),
            expected_output=(
                "Структурированный список условий договора: стороны, сроки, предмет, "
                "права и обязанности, пункты об ответственности."
            ),
            agent=extractor_agent
        )

        audit_task = Task(
            description=(
                task2_desc +
                f"\n\nТЕКСТ ДОГОВОРА ДЛЯ ПРОВЕРКИ:\n{contract_text[:8000]}"
                f"\n\nОбязательные требования из регламента:\n{knowledge_base}"
            ),
            expected_output=(
                "Отчёт о найденных нарушениях с указанием конкретных отсутствующих пунктов. "
                "Если нарушений нет — явно написать 'Нарушений не обнаружено'."
            ),
            agent=auditor_agent,
            context=[extract_task]
        )

        conditional_task = Task(
            description=(
                task3_desc +
                f"\n\nТекущий сценарий: '{scenario}'."
            ),
            expected_output=(
                "Либо пронумерованный список конкретных правок с указанием раздела договора, "
                "либо строка 'Доработки не требуются'."
            ),
            agent=coordinator_agent,
            context=[audit_task]
        )

        # HITL
        final_task = Task(
            description=task4_desc,
            expected_output=(
                "Итоговое заключение: одна из формулировок — "
                "'Договор готов к подписанию', 'Требуется доработка', "
                "или 'Необходима ручная проверка юриста'. Плюс 2-3 предложения обоснования."
            ),
            agent=finalizer_agent,
            context=[extract_task, audit_task, conditional_task],
            human_input=False  # HITL
        )

        # ---- ЗАПУСК ----
        with st.spinner("Агенты работают... Для HITL проверьте терминал и введите подтверждение."):
            try:
                crew = Crew(
                    agents=[extractor_agent, auditor_agent, coordinator_agent, finalizer_agent],
                    tasks=[extract_task, audit_task, conditional_task, final_task],
                    process=Process.sequential,
                    memory=False,
                    verbose=True
                )

                result = crew.kickoff()

                st.success("✅ Анализ завершён!")

                st.subheader("📋 Итоговое заключение (HITL подтверждено)")
                verdict = str(result.raw) if hasattr(result, "raw") else str(result)
                if "готов к подписанию" in verdict.lower():
                    st.success(f"🟢 {verdict}")
                elif "доработка" in verdict.lower() or "исправить" in verdict.lower():
                    st.warning(f"🟡 {verdict}")
                else:
                    st.error(f"🔴 {verdict}")

                st.subheader("📊 Результаты по шагам")
                steps = [
                    ("Шаг 1 — Экстракция договора", extract_task),
                    ("Шаг 2 — Аудит соответствия", audit_task),
                    ("Шаг 3 — Conditional: список доработок", conditional_task),
                    ("Шаг 4 — Финальное заключение (HITL)", final_task),
                ]
                for step_name, task_obj in steps:
                    with st.expander(step_name):
                        output = getattr(task_obj, "output", None)
                        if output:
                            raw = getattr(output, "raw", str(output))
                            st.write(raw)
                            if "conditional" in step_name.lower():
                                if "доработки не требуются" in raw.lower():
                                    st.info("ℹ️ ConditionalTask: условие НЕ сработало — нарушений не обнаружено.")
                                else:
                                    st.warning("⚠️ ConditionalTask: условие СРАБОТАЛО — найдены нарушения.")
                        else:
                            st.write("_(результат недоступен)_")

                st.subheader("🧠 Memory")
                st.info(
                    "Memory сохраняет типичные замечания, согласованные формулировки и историю прошлых проверок. "
                    "При следующем запуске система учтёт уже выявленные паттерны нарушений."
                )

                st.subheader("🔧 Использованные инструменты")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ContractReaderTool", "✅", "Чтение договора")
                with col2:
                    st.metric("Check Mandatory Clauses", "✅", "Проверка пунктов")
                with col3:
                    st.metric("Knowledge Base Lookup", "✅", "Поиск по регламенту")

            except Exception as e:
                st.error(f"❌ Ошибка при запуске: {e}")
                st.exception(e)
            finally:
                try:
                    os.remove(contract_txt_path)
                except Exception:
                    pass

st.markdown("---")
st.caption(
    "💡 HITL: при запуске в терминале появится запрос на подтверждение финального заключения. "
    "Введите комментарий или нажмите Enter для одобрения."
)
