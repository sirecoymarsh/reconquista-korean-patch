"""Mouse, window mode, chapter search, choice-option jump (run A); viewpoint jump, global search, close-while-open (run B)."""
import time

import qa
import read_storymap

VK = dict(F11=0x7a, TAB=0x09, RET=0x0d, ESC=0x1b, LEFT=0x25, UP=0x26, RIGHT=0x27, DOWN=0x28, F1=0x70, HOME=0x24)
data = read_storymap.parse(qa.RUN / 'storymap.bin')
chap = {c['id']: i for i, c in enumerate(data['chapters'])}


def center(cid):
    r = data['chapters'][chap[cid]]['rect']
    return (r[0] + r[2]) / 20, (r[1] + r[3]) / 20


def boot(g):
    g.until(lambda: 'asset 1de0628c ' in g.log(), 90, 'title')
    g.hwnd = next(x['h'] for x in g.windows() if x['class'] == 'MAJIRO_EXEC_CLASS')
    time.sleep(1)
    for m, a in [(0x1c, 1), (6, 1), (7, 0)]:
        qa.u.SendMessageW(g.hwnd, m, a, 0)


def open_chart(g):
    n = g.count('inflow opened')
    g.key(g.hwnd, VK['F11'])
    g.until(lambda: g.count('inflow opened') > n, 20, 'open')
    return g.child()


def step_to_kind(g, child, kind, scenes=12, limit=200):
    """Walk the items of the selected scene; move to the next found scene when this one has no such row."""
    for _ in range(scenes):
        last = None
        for _ in range(limit):
            n = g.count('item=')
            g.key(child, VK['DOWN'], 1, 0)
            g.until(lambda: g.count('item=') > n, 5, 'item step')
            tail = g.log().split('inflow item=')[-1][:40]
            if f'kind={kind} ' in tail:
                return g.last('order=')
            if tail == last:
                break
            last = tail
        n = g.count('scene=')
        g.key(child, VK['RIGHT'])
        g.until(lambda: g.count('scene=') > n, 5, 'next scene')
    raise RuntimeError('kind not found')


def jump_and_arrive(g, child):
    n = g.count('inflow jump order=')
    g.story_jump(child)
    g.until(lambda: g.count('inflow jump order=') > n, 10, 'jump request')
    order = g.last('inflow jump order=')
    g.until(lambda: f'inflow arrived order={order} ' in g.log(), 150, 'arrival')
    return order


def run_a(result):
    g = qa.Game()
    try:
        boot(g)
        n = g.count('mode full=0')
        g.post(g.hwnd, 0x104, 0x0d, 1 << 29)              # Alt+Enter -> window mode
        g.until(lambda: g.count('mode full=0') > n, 15, 'window mode')
        s = g.count('inflow snapshot')
        child = open_chart(g)
        g.snapshot('m01-window-map', s)
        result['window_render'] = g.log().split('inflow render')[-1].split('\n')[0]
        x, y = center('kureha_10')
        g.move(child, x, y)
        g.until(lambda: f"hover={chap['kureha_10']}" in g.log(), 5, 'hover')
        result['tests'].append('hover_cell')
        for want in (1, 0):
            n = g.count(f'page={want}')
            g.logical_click(child, 445, 35)
            g.until(lambda: g.count(f'page={want}') > n, 5, 'purple plate')
        result['tests'].append('purple_plate_toggles_page')
        n = g.count('page=2 chapter=')
        s = g.count('inflow snapshot')
        g.logical_click(child, 576, 48)                    # 지금 자리로: cursor to the current chapter, or open it if already there
        g.until(lambda: g.count('inflow snapshot') > s, 5, 'gold')
        time.sleep(.3)
        if g.count('page=2 chapter=') == n:
            g.logical_click(child, 576, 48)
            g.until(lambda: g.count('page=2 chapter=') > n, 5, 'gold opens chapter')
        result['current_chapter_opened'] = g.log().split('page=2 chapter=')[-1].split()[0]
        result['tests'].append('gold_plate_current_then_open')
        n = g.count('scene=')
        g.logical_click(child, 120, 110 + 56 + 20)        # second scene card
        g.until(lambda: g.count('scene=') > n, 5, 'scene card')
        n = g.count('inflow wheel')
        g.wheel(child, 500, 300, -2)
        g.until(lambda: g.count('inflow wheel') > n, 5, 'wheel')
        n = g.count('item=')
        g.logical_click(child, 500, 140)
        g.until(lambda: g.count('item=') > n, 5, 'line click')
        result['tests'].append('scene_card_wheel_line_click')
        g.logical_click(child, 400, 101)                   # search box
        time.sleep(.4)
        edit = g.edit()
        assert edit
        s = g.count('inflow snapshot')
        g.chars(edit, '마호')
        g.until(lambda: 'search len=2 ' in g.log(), 5, 'search typed')
        g.snapshot('m02-search-chapter', s)
        result['search_maho'] = g.log().split('search len=2 ')[-1].split('\n')[0]
        for _ in range(2):
            g.post(edit, 0x102, 8)                         # backspace x2
            time.sleep(.1)
        g.chars(edit, '못 들은')
        g.until(lambda: 'search len=4 ' in g.log(), 5, 'search option')
        order = step_to_kind(g, child, 2)
        result['choice_option_order'] = order
        s = g.count('inflow snapshot')
        arrived = jump_and_arrive(g, child)
        result['tests'].append(f'choice_option_jump_arrived_{arrived}')
        time.sleep(3)
        child = open_chart(g)
        g.key(child, VK['ESC'])
        g.until(lambda: 'inflow closed_resume' in g.log(), 10, 'close')
        result['tests'].append('reopen_close_after_option_jump')
    finally:
        result['a_normal_exit'] = g.close_normally()
        (qa.QA / 'test_more_a.log').write_text(g.log(), 'utf-8')


def run_b(result):
    g = qa.Game()
    try:
        boot(g)
        child = open_chart(g)
        x, y = center('00_レコンキスタ_start_2')
        n = g.count('page=2 chapter=')
        g.logical_click(child, x, y)                      # click the 도입부 2 cell
        g.until(lambda: g.count('page=2 chapter=') > n, 5, 'cell click opens chapter')
        g.logical_click(child, 400, 101)
        time.sleep(.4)
        g.chars(g.edit(), '미사와')
        g.until(lambda: 'search len=3 ' in g.log(), 5, 'search view')
        order = step_to_kind(g, child, 4)
        result['view_option_order'] = order
        arrived = jump_and_arrive(g, child)
        result['tests'].append(f'viewpoint_jump_arrived_{arrived}')
        time.sleep(3)
        child = open_chart(g)
        n = g.count('search_all')
        g.logical_click(child, 576, 20)                    # 대사 찾기 plate -> all chapters
        g.until(lambda: g.count('search_all') > n, 5, 'search all')
        time.sleep(.4)
        g.chars(g.edit(), '드디어 만났')
        g.until(lambda: 'search len=6 ' in g.log(), 5, 'global search')
        result['global_search'] = g.log().split('search len=6 ')[-1].split('\n')[0]
        result['tests'].append('global_search')
        g.key(child, VK['ESC'])                            # back to map
        time.sleep(.3)
        g.post(g.hwnd, 0x10)                               # close the game while the map is open
        deadline = time.time() + 15
        while g.poll() is None and time.time() < deadline:
            for w in g.windows():
                if w['class'] == '#32770':
                    g.post(w['h'], 0x111, 6, 0)
            time.sleep(.25)
        result['b_exit_while_open'] = g.poll() is not None
        result['tests'].append('close_game_while_map_open')
    finally:
        result['b_normal_exit'] = g.close_normally()
        (qa.QA / 'test_more_b.log').write_text(g.log(), 'utf-8')


if __name__ == '__main__':
    import sys
    result = {'tests': []}
    before = qa.savehash()
    try:
        if 'b' not in sys.argv[1:]:
            run_a(result)
        run_b(result)
        result['pass'] = True
    except Exception as e:
        result['error'] = repr(e)
        print('ERROR', repr(e))
    result['savedata_unchanged'] = qa.savehash() == before
    qa.dump('test_more.json', result)
    print(result)
