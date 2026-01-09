import flet as ft
import json
import random
import os
import copy

# --- КОНФИГУРАЦИЯ ---
EXAM_CONFIG = {
    "КОМПРЕССИЯ": ["030", "021", "КПГ", "этилен", "пропилен", "122", "125-14; 121-05", "031", "020"],
    "НТГ": ["028", "030", "032", "023", "024; 121-06", "025", "026; 027"],
    "ВТГ": ["037; 121-07", "038; 121-08", "022; 125-04", "150", "033", "034", "035", "036"]
}

FILES_PATH = "questions.json"

def main(page: ft.Page):
    # --- НАСТРОЙКИ UI ---
    page.title = "Экзаменатор Онлайн"
    
    # В версии 0.25.2 это работает отлично:
    page.theme = ft.Theme(
        color_scheme_seed="indigo", 
        visual_density=ft.ThemeVisualDensity.COMPACT
    )
    page.theme_mode = "light"
    page.padding = 0
    page.bgcolor = "#F2F4F7"
    # Для веба разрешаем скролл
    page.scroll = "auto"

    # --- ДАННЫЕ ---
    full_data = {}
    current_questions = []
    current_answers = {}
    current_topic = ""

    if os.path.exists(FILES_PATH):
        try:
            with open(FILES_PATH, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
        except:
            pass
    
    if not full_data:
        page.add(ft.Container(content=ft.Text("Ошибка: questions.json пуст или не найден"), padding=20))
        return

    # --- ЛОГИКА (Работает с хранилищем браузера) ---
    def save_stats(topic, correct, total):
        stats = page.client_storage.get("user_stats") or {}
        if topic not in stats: stats[topic] = {'correct': 0, 'total': 0}
        stats[topic]['correct'] += correct
        stats[topic]['total'] += total
        page.client_storage.set("user_stats", stats)

    def get_stats():
        return page.client_storage.get("user_stats") or {}

    def start_session(key, mode):
        nonlocal current_questions, current_answers, current_topic
        pool = []
        if mode == 'exam':
            for b in EXAM_CONFIG.get(key, []):
                if b in full_data: pool.extend(full_data[b])
        else:
            pool = full_data.get(key, [])
            
        if not pool:
            # Старый добрый SnackBar
            page.snack_bar = ft.SnackBar(content=ft.Text("Вопросов нет"))
            page.snack_bar.open = True
            page.update()
            return

        final_pool = []
        for q in pool:
            new_q = copy.deepcopy(q)
            opts = [str(o) for o in new_q['options']]
            if new_q['correct'] < len(opts):
                corr_txt = opts[new_q['correct']]
                random.shuffle(opts)
                new_q['options'] = opts
                new_q['correct'] = opts.index(corr_txt)
                final_pool.append(new_q)
            else:
                final_pool.append(new_q)

        current_topic = key
        current_answers = {}
        
        if mode == 'exam':
            current_questions = random.sample(final_pool, min(len(final_pool), 20))
            show_test_screen()
        elif mode == 'ticket':
            random.shuffle(final_pool)
            current_questions = final_pool
            show_test_screen()
        elif mode == 'study':
            current_questions = final_pool
            show_study_screen()

    # --- КОМПОНЕНТЫ UI ---

    def grid_item(title, count, icon, color, on_click):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, color=color, size=24),
                ft.Text(title, weight="bold", size=13, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{count} вопр.", size=11, color="grey")
            ], alignment="center", spacing=2),
            bgcolor="white",
            border_radius=12,
            padding=10,
            on_click=on_click,
            # В 0.25.2 with_opacity работает отлично
            shadow=ft.BoxShadow(blur_radius=5, color=ft.colors.with_opacity(0.1, "black")),
            alignment=ft.alignment.center
        )

    # --- ЭКРАН 1: ГЛАВНОЕ МЕНЮ ---
    def show_menu_screen():
        page.clean()
        
        exam_grid = ft.GridView(
            expand=True, runs_count=2, max_extent=160, child_aspect_ratio=1.5, spacing=10, run_spacing=10, padding=15
        )
        for key in EXAM_CONFIG:
            count = sum(len(full_data.get(b, [])) for b in EXAM_CONFIG[key] if b in full_data)
            exam_grid.controls.append(grid_item(key, count, ft.icons.SCHOOL, "indigo", lambda e, k=key: start_session(k, 'exam')))

        study_list = ft.ListView(expand=True, spacing=5, padding=10)
        for key in sorted(full_data.keys()):
            count = len(full_data[key])
            study_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.MENU_BOOK, size=18, color="blue"),
                        ft.Text(key, size=14, weight="bold", expand=True),
                        ft.Text(str(count), size=12, color="grey"),
                        ft.Icon(ft.icons.CHEVRON_RIGHT, size=16, color="grey")
                    ], alignment="spaceBetween"),
                    bgcolor="white", padding=12, border_radius=8,
                    on_click=lambda e, k=key: start_session(k, 'study')
                )
            )

        ticket_list = ft.ListView(expand=True, spacing=5, padding=10)
        for key in sorted(full_data.keys()):
            count = len(full_data[key])
            ticket_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CONFIRMATION_NUMBER, size=18, color="purple"),
                        ft.Text(key, size=14, weight="bold", expand=True),
                        ft.Icon(ft.icons.CHEVRON_RIGHT, size=16, color="grey")
                    ]),
                    bgcolor="white", padding=12, border_radius=8,
                    on_click=lambda e, k=key: start_session(k, 'ticket')
                )
            )

        stats_list = ft.ListView(expand=True, spacing=10, padding=15)
        stats = get_stats()
        
        if stats:
            total_corr = sum(v['correct'] for v in stats.values())
            total_all = sum(v['total'] for v in stats.values())
            total_perc = int((total_corr/total_all)*100) if total_all else 0
            
            stats_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text("Общая эффективность", size=12, color="grey"),
                            ft.Text(f"{total_perc}%", size=24, weight="bold", color="indigo")
                        ]),
                        ft.Icon(ft.icons.PIE_CHART, size=40, color="indigo")
                    ], alignment="spaceBetween"),
                    bgcolor="white", padding=20, border_radius=15, margin=ft.margin.only(bottom=10)
                )
            )

            for k, v in stats.items():
                perc = int((v['correct']/v['total'])*100) if v['total'] > 0 else 0
                color = "green" if perc > 70 else ("orange" if perc > 40 else "red")
                stats_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([ft.Text(k, size=13, weight="bold"), ft.Text(f"{perc}%", size=13, color=color, weight="bold")], alignment="spaceBetween"),
                            ft.ProgressBar(value=perc/100, color=color, bgcolor="#EEF2F6", height=6)
                        ]),
                        bgcolor="white", padding=12, border_radius=10
                    )
                )
            
            stats_list.controls.append(
                ft.TextButton(content=ft.Text("Сбросить статистику", color="red"), on_click=lambda e: [page.client_storage.remove("user_stats"), show_menu_screen()])
            )
        else:
            stats_list.controls.append(ft.Text("Нет данных", text_align="center", color="grey"))


        content_switcher = ft.AnimatedSwitcher(
            content=exam_grid,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            reverse_duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_IN,
            switch_out_curve=ft.AnimationCurve.EASE_OUT,
        )

        def on_nav_change(e):
            idx = e.control.selected_index
            if idx == 0: content_switcher.content = exam_grid
            elif idx == 1: content_switcher.content = study_list
            elif idx == 2: content_switcher.content = ticket_list
            elif idx == 3: content_switcher.content = stats_list
            content_switcher.update()

        page.add(
            ft.Column([
                ft.Container(
                    content=ft.Text("Экзаменатор", size=18, weight="bold", color="indigo"),
                    padding=ft.padding.only(left=20, top=15, bottom=10),
                    bgcolor="#F2F4F7"
                ),
                ft.Container(content=content_switcher, expand=True)
            ], expand=True),
            # Стандартный NavigationBar отлично работает в 0.25.2
            ft.NavigationBar(
                selected_index=0,
                destinations=[
                    ft.NavigationDestination(icon=ft.icons.SCHOOL, label="Экзамен"),
                    ft.NavigationDestination(icon=ft.icons.MENU_BOOK, label="Учеба"),
                    ft.NavigationDestination(icon=ft.icons.CONFIRMATION_NUMBER, label="Билеты"),
                    ft.NavigationDestination(icon=ft.icons.BAR_CHART, label="Прогресс"),
                ],
                on_change=on_nav_change
            )
        )
        page.update()

    # --- ЭКРАН 2: ТЕСТ ---
    def show_test_screen():
        page.clean()
        
        content_col = ft.Column(scroll="auto", expand=True, spacing=15)
        
        def render_step(idx):
            content_col.controls.clear()
            
            if idx >= len(current_questions):
                show_result_screen()
                return

            q = current_questions[idx]
            
            rg = ft.RadioGroup(content=ft.Column(spacing=8))
            rg.on_change = lambda e: current_answers.update({idx: int(e.data)})
            
            if idx in current_answers: 
                rg.value = str(current_answers[idx])

            for i, opt in enumerate(q['options']):
                rg.content.controls.append(
                    ft.Container(
                        content=ft.Radio(value=str(i), label=opt, label_position="right"),
                        bgcolor="white", padding=8, border_radius=8, border=ft.border.all(1, "#E0E0E0")
                    )
                )

            progress_val = (idx+1)/len(current_questions) if len(current_questions) > 0 else 0
            progress = ft.ProgressBar(value=progress_val, color="indigo", bgcolor="#E0E0E0", height=4)
            
            top_bar = ft.Container(
                content=ft.Row([
                    ft.IconButton(ft.icons.ARROW_BACK, icon_size=20, on_click=lambda e: show_menu_screen()),
                    ft.Text(f"Вопрос {idx+1} из {len(current_questions)}", size=14, weight="bold"),
                    ft.Container(width=40)
                ], alignment="spaceBetween"),
                bgcolor="white", padding=5
            )
            
            content_col.controls.extend([
                ft.Container(
                    content=ft.Text(q['q'], weight="bold", size=15),
                    bgcolor="white", padding=15, border_radius=12,
                    shadow=ft.BoxShadow(blur_radius=5, color="#E0E0E0")
                ),
                rg,
                ft.Container(height=10),
                ft.ElevatedButton(
                    text="Подтвердить",
                    width=float("inf"),
                    height=45,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: render_step(idx + 1) if rg.value else page.open(ft.SnackBar(content=ft.Text("Выберите ответ!")))
                )
            ])
            
            page.clean()
            page.add(
                top_bar,
                progress,
                ft.Container(content=content_col, padding=15, expand=True)
            )
            page.update()

        render_step(0)

    # --- ЭКРАН 3: ОБУЧЕНИЕ ---
    def show_study_screen():
        page.clean()
        
        lv = ft.ListView(expand=True, spacing=10, padding=15)
        
        for i, q in enumerate(current_questions, 1):
            opts = ft.Column(spacing=2)
            for idx, opt in enumerate(q['options']):
                is_corr = (idx == q['correct'])
                color = "green" if is_corr else "grey"
                weight = "bold" if is_corr else "normal"
                icon = ft.icons.CHECK if is_corr else ft.icons.CIRCLE
                size = 18 if is_corr else 10
                
                opts.controls.append(
                    ft.Row([
                        ft.Icon(icon, size=size, color=color),
                        ft.Text(opt, size=13, color=color, weight=weight, expand=True)
                    ], vertical_alignment="start")
                )
            
            lv.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{i}. {q['q']}", size=14, weight="bold"),
                        ft.Divider(height=5, color="transparent"),
                        opts
                    ]),
                    bgcolor="white", padding=12, border_radius=10,
                    border=ft.border.all(1, "#E0E0E0" if i % 2 == 0 else "transparent")
                )
            )

        page.add(
            ft.Container(
                content=ft.Row([
                    ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda e: show_menu_screen()),
                    ft.Text("База знаний", weight="bold")
                ]),
                bgcolor="white", padding=5
            ),
            ft.Container(content=lv, expand=True)
        )
        page.update()

    # --- ЭКРАН 4: РЕЗУЛЬТАТ ---
    def show_result_screen():
        page.clean()
        score = sum(1 for i, q in enumerate(current_questions) if current_answers.get(i) == q['correct'])
        total = len(current_questions)
        perc = int((score/total)*100) if total > 0 else 0
        save_stats(current_topic, score, total)
        
        color = "green" if perc > 70 else ("orange" if perc > 40 else "red")
        
        mistakes = ft.Column(spacing=10, scroll="auto")
        for i, q in enumerate(current_questions):
            u = current_answers.get(i)
            c = q['correct']
            if u != c:
                mistakes.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(q['q'], size=13, weight="bold"),
                            ft.Text(f"Ваш ответ: {q['options'][u] if u is not None else '-'}", color="red", size=12),
                            ft.Text(f"Верно: {q['options'][c]}", color="green", size=12)
                        ]),
                        bgcolor="white", padding=10, border_radius=8, border=ft.border.all(1, "#FFEBEE")
                    )
                )

        if not mistakes.controls:
             mistakes.controls.append(ft.Text("Ошибок нет!", color="green", text_align="center"))

        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Container(height=20),
                    ft.Text("Результат", color="grey"),
                    ft.Text(f"{perc}%", size=40, weight="bold", color=color),
                    ft.Text(f"{score} / {total}", weight="bold"),
                    ft.Divider(),
                    ft.Text("Работа над ошибками:", size=12, weight="bold"),
                    ft.Container(content=mistakes, expand=True),
                    ft.Container(
                        content=ft.ElevatedButton(
                            text="В меню",
                            width=float("inf"),
                            on_click=lambda e: show_menu_screen()
                        ),
                        padding=ft.padding.only(top=10)
                    )
                ], horizontal_alignment="center"),
                alignment=ft.alignment.center,
                expand=True, padding=20
            )
        )
        page.update()

    show_menu_screen()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)