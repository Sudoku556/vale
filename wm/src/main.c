#include <xcb/xcb.h>
#include <xcb/xcb_keysyms.h>
#include <xcb/xcb_icccm.h>
#include <xcb/xcb_ewmh.h>
#include <cairo/cairo.h>
#include <cairo/cairo-xcb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>

#define TITLEBAR_HEIGHT 24
#define BORDER_MARGIN 6
#define BUTTON_SIZE 14
#define MIN_SIZE 80
#define ANIM_STEPS 8
#define ANIM_STEP_US 15000
#define COLOR_TITLEBAR 0x2a2a3a
#define COLOR_ACTIVE_TITLEBAR 0x5b3a80
#define COLOR_CLOSE 0xff757f
#define COLOR_MAX 0x41a6b5
#define COLOR_MIN 0xffc777

enum { EDGE_NONE, EDGE_LEFT, EDGE_RIGHT, EDGE_BOTTOM, EDGE_BOTTOMLEFT, EDGE_BOTTOMRIGHT };

typedef struct Client {
    xcb_window_t window;
    xcb_window_t frame;
    int16_t x, y;
    uint16_t w, h;
    int16_t orig_x, orig_y;
    uint16_t orig_w, orig_h;
    int is_maximized;
    char title[128];
    struct Client *next;
} Client;

static Client *clients = NULL;
static xcb_connection_t *c;
static xcb_screen_t *screen;
static xcb_gcontext_t gc;
static xcb_key_symbols_t *keysyms = NULL;
static xcb_keycode_t super_keycode = 0;
static xcb_cursor_t default_cursor = 0;
static xcb_visualtype_t *visual_type = NULL;

static int is_dragging = 0, is_resizing = 0, resize_edge = EDGE_NONE;
static int16_t drag_start_x = 0, drag_start_y = 0;
static Client *drag_client = NULL;
static Client *active_client = NULL;

typedef struct { xcb_keysym_t keysym; const char *cmd; xcb_keycode_t keycode; } Hotkey;
static Hotkey hotkeys[] = {
    { 0x1008FF13, "pactl set-sink-volume @DEFAULT_SINK@ +5%", 0 },
    { 0x1008FF11, "pactl set-sink-volume @DEFAULT_SINK@ -5%", 0 },
    { 0x1008FF12, "pactl set-sink-mute @DEFAULT_SINK@ toggle", 0 },
    { 0xff61, "mkdir -p ~/Pictures && scrot ~/Pictures/vale_%Y-%m-%d_%H-%M-%S.png", 0 },
};
#define NUM_HOTKEYS (sizeof(hotkeys) / sizeof(hotkeys[0]))

static xcb_visualtype_t *find_visual_type(xcb_screen_t *scr) {
    xcb_depth_iterator_t depth_iter = xcb_screen_allowed_depths_iterator(scr);
    for (; depth_iter.rem; xcb_depth_next(&depth_iter)) {
        xcb_visualtype_iterator_t visual_iter = xcb_depth_visuals_iterator(depth_iter.data);
        for (; visual_iter.rem; xcb_visualtype_next(&visual_iter)) {
            if (scr->root_visual == visual_iter.data->visual_id)
                return visual_iter.data;
        }
    }
    return NULL;
}

static Client *find_by_window(xcb_window_t win) {
    for (Client *cl = clients; cl; cl = cl->next) if (cl->window == win) return cl;
    return NULL;
}
static Client *find_by_frame(xcb_window_t win) {
    for (Client *cl = clients; cl; cl = cl->next) if (cl->frame == win) return cl;
    return NULL;
}
static void remove_client(Client *target) {
    if (!target) return;
    if (clients == target) { clients = target->next; }
    else {
        for (Client *cl = clients; cl; cl = cl->next) {
            if (cl->next == target) { cl->next = target->next; break; }
        }
    }
    free(target);
}

static void fetch_title(Client *cl) {
    strcpy(cl->title, "Untitled");
    xcb_icccm_get_text_property_reply_t reply;
    xcb_get_property_cookie_t cookie = xcb_icccm_get_wm_name(c, cl->window);
    if (xcb_icccm_get_wm_name_reply(c, cookie, &reply, NULL)) {
        size_t len = reply.name_len < 127 ? reply.name_len : 127;
        memcpy(cl->title, reply.name, len);
        cl->title[len] = '\0';
        xcb_icccm_get_text_property_reply_wipe(&reply);
    }
}

static void run_shell(const char *cmd) {
    if (fork() == 0) {
        setsid();
        execl("/bin/sh", "sh", "-c", cmd, (char *)NULL);
        _exit(1);
    }
}

static void spawn_launcher(void) {
    if (fork() == 0) {
        setsid();
        const char *home = getenv("HOME");
        char path[512];
        snprintf(path, sizeof(path), "%s/vale/launcher/vale-launcher.py", home ? home : "");
        execlp("python3", "python3", path, (char *)NULL);
        _exit(1);
    }
}

static void draw_frame(Client *cl);

static void focus_and_raise(Client *cl) {
    if (!cl) return;
    Client *prev = active_client;
    active_client = cl;
    uint32_t stack_val[1] = { XCB_STACK_MODE_ABOVE };
    xcb_configure_window(c, cl->frame, XCB_CONFIG_WINDOW_STACK_MODE, stack_val);
    xcb_set_input_focus(c, XCB_INPUT_FOCUS_POINTER_ROOT, cl->window, XCB_CURRENT_TIME);
    xcb_flush(c);
    if (prev && prev != cl) draw_frame(prev);
    draw_frame(cl);
}

static void kill_client_window(xcb_window_t win) {
    xcb_intern_atom_cookie_t cookie_wm = xcb_intern_atom(c, 0, 12, "WM_PROTOCOLS");
    xcb_intern_atom_cookie_t cookie_del = xcb_intern_atom(c, 0, 16, "WM_DELETE_WINDOW");
    xcb_intern_atom_reply_t *rep_wm = xcb_intern_atom_reply(c, cookie_wm, NULL);
    xcb_intern_atom_reply_t *rep_del = xcb_intern_atom_reply(c, cookie_del, NULL);

    if (rep_wm && rep_del) {
        xcb_client_message_event_t ev = {0};
        ev.response_type = XCB_CLIENT_MESSAGE;
        ev.window = win;
        ev.type = rep_wm->atom;
        ev.format = 32;
        ev.data.data32[0] = rep_del->atom;
        ev.data.data32[1] = XCB_CURRENT_TIME;
        xcb_send_event(c, 0, win, XCB_EVENT_MASK_NO_EVENT, (char *)&ev);
    } else {
        xcb_kill_client(c, win);
    }
    free(rep_wm);
    free(rep_del);
    xcb_flush(c);
}

static void apply_geometry(Client *cl) {
    uint32_t frame_values[4] = {
        (uint32_t)(int32_t)cl->x, (uint32_t)(int32_t)cl->y,
        (uint32_t)(cl->w + 2 * BORDER_MARGIN),
        (uint32_t)(cl->h + TITLEBAR_HEIGHT + BORDER_MARGIN)
    };
    xcb_configure_window(c, cl->frame,
        XCB_CONFIG_WINDOW_X | XCB_CONFIG_WINDOW_Y | XCB_CONFIG_WINDOW_WIDTH | XCB_CONFIG_WINDOW_HEIGHT,
        frame_values);
    uint32_t win_values[2] = { cl->w, cl->h };
    xcb_configure_window(c, cl->window, XCB_CONFIG_WINDOW_WIDTH | XCB_CONFIG_WINDOW_HEIGHT, win_values);
}

static void toggle_maximize(Client *client) {
    if (!client) return;
    if (!client->is_maximized) {
        client->orig_x = client->x; client->orig_y = client->y;
        client->orig_w = client->w; client->orig_h = client->h;
        client->x = 0; client->y = 0;
        client->w = screen->width_in_pixels - 2 * BORDER_MARGIN;
        client->h = screen->height_in_pixels - TITLEBAR_HEIGHT - BORDER_MARGIN;
        client->is_maximized = 1;
    } else {
        client->x = client->orig_x; client->y = client->orig_y;
        client->w = client->orig_w; client->h = client->orig_h;
        client->is_maximized = 0;
    }
    apply_geometry(client);
    xcb_flush(c);
}

static void animate_open(Client *cl) {
    uint16_t final_fw = cl->w + 2 * BORDER_MARGIN;
    uint16_t final_fh = cl->h + TITLEBAR_HEIGHT + BORDER_MARGIN;
    int16_t cx = cl->x + final_fw / 2;
    int16_t cy = cl->y + final_fh / 2;

    for (int step = 1; step <= ANIM_STEPS; step++) {
        double t = (double)step / ANIM_STEPS;
        uint16_t fw = (uint16_t)(final_fw * t); if (fw < 10) fw = 10;
        uint16_t fh = (uint16_t)(final_fh * t); if (fh < 10) fh = 10;
        int16_t x = cx - fw / 2;
        int16_t y = cy - fh / 2;
        uint32_t vals[4] = { (uint32_t)(int32_t)x, (uint32_t)(int32_t)y, fw, fh };
        xcb_configure_window(c, cl->frame,
            XCB_CONFIG_WINDOW_X | XCB_CONFIG_WINDOW_Y | XCB_CONFIG_WINDOW_WIDTH | XCB_CONFIG_WINDOW_HEIGHT, vals);
        xcb_flush(c);
        usleep(ANIM_STEP_US);
    }
    apply_geometry(cl);
    draw_frame(cl);
    xcb_flush(c);
}

static void animate_close(Client *cl) {
    uint16_t final_fw = cl->w + 2 * BORDER_MARGIN;
    uint16_t final_fh = cl->h + TITLEBAR_HEIGHT + BORDER_MARGIN;
    int16_t cx = cl->x + final_fw / 2;
    int16_t cy = cl->y + final_fh / 2;

    for (int step = ANIM_STEPS - 1; step >= 1; step--) {
        double t = (double)step / ANIM_STEPS;
        uint16_t fw = (uint16_t)(final_fw * t); if (fw < 10) fw = 10;
        uint16_t fh = (uint16_t)(final_fh * t); if (fh < 10) fh = 10;
        int16_t x = cx - fw / 2;
        int16_t y = cy - fh / 2;
        uint32_t vals[4] = { (uint32_t)(int32_t)x, (uint32_t)(int32_t)y, fw, fh };
        xcb_configure_window(c, cl->frame,
            XCB_CONFIG_WINDOW_X | XCB_CONFIG_WINDOW_Y | XCB_CONFIG_WINDOW_WIDTH | XCB_CONFIG_WINDOW_HEIGHT, vals);
        xcb_flush(c);
        usleep(ANIM_STEP_US);
    }
    xcb_unmap_window(c, cl->frame);
    xcb_flush(c);
}

static void frame_window(xcb_window_t win) {
    if (find_by_window(win)) return;

    xcb_get_geometry_reply_t *geom = xcb_get_geometry_reply(c, xcb_get_geometry(c, win), NULL);
    if (!geom) return;

    xcb_window_t frame = xcb_generate_id(c);
    uint32_t mask = XCB_CW_BACK_PIXEL | XCB_CW_EVENT_MASK | XCB_CW_CURSOR;
    uint32_t values[3] = {
        COLOR_TITLEBAR,
        XCB_EVENT_MASK_EXPOSURE | XCB_EVENT_MASK_BUTTON_PRESS | XCB_EVENT_MASK_BUTTON_RELEASE |
        XCB_EVENT_MASK_BUTTON_1_MOTION | XCB_EVENT_MASK_SUBSTRUCTURE_NOTIFY,
        default_cursor
    };
    xcb_create_window(c, screen->root_depth, frame, screen->root,
                      geom->x, geom->y,
                      geom->width + 2 * BORDER_MARGIN,
                      geom->height + TITLEBAR_HEIGHT + BORDER_MARGIN, 0,
                      XCB_WINDOW_CLASS_INPUT_OUTPUT, screen->root_visual, mask, values);

    xcb_reparent_window(c, win, frame, BORDER_MARGIN, TITLEBAR_HEIGHT);
    xcb_map_window(c, frame);
    xcb_map_window(c, win);

    uint32_t prop_mask[1] = { XCB_EVENT_MASK_PROPERTY_CHANGE };
    xcb_change_window_attributes(c, win, XCB_CW_EVENT_MASK, prop_mask);

    Client *client = calloc(1, sizeof(Client));
    client->window = win; client->frame = frame;
    client->x = geom->x; client->y = geom->y;
    client->w = geom->width; client->h = geom->height;
    client->next = clients;
    clients = client;
    fetch_title(client);

    xcb_grab_button(c, 0, win, XCB_EVENT_MASK_BUTTON_PRESS,
                    XCB_GRAB_MODE_SYNC, XCB_GRAB_MODE_ASYNC,
                    XCB_NONE, XCB_NONE, XCB_BUTTON_INDEX_1, XCB_MOD_MASK_ANY);

    xcb_grab_button(c, 0, frame, XCB_EVENT_MASK_BUTTON_PRESS | XCB_EVENT_MASK_BUTTON_RELEASE | XCB_EVENT_MASK_BUTTON_MOTION,
                    XCB_GRAB_MODE_ASYNC, XCB_GRAB_MODE_ASYNC, XCB_NONE, XCB_NONE, 1, XCB_MOD_MASK_1);
    xcb_grab_button(c, 0, frame, XCB_EVENT_MASK_BUTTON_PRESS | XCB_EVENT_MASK_BUTTON_RELEASE | XCB_EVENT_MASK_BUTTON_MOTION,
                    XCB_GRAB_MODE_ASYNC, XCB_GRAB_MODE_ASYNC, XCB_NONE, XCB_NONE, 3, XCB_MOD_MASK_1);

    xcb_flush(c);
    free(geom);

    focus_and_raise(client);
    animate_open(client);
}

static void draw_frame(Client *cl) {
    if (!cl) return;
    uint16_t frame_w = cl->w + 2 * BORDER_MARGIN;

    uint32_t val = (cl == active_client) ? COLOR_ACTIVE_TITLEBAR : COLOR_TITLEBAR;
    xcb_change_gc(c, gc, XCB_GC_FOREGROUND, &val);
    xcb_rectangle_t bg = { 0, 0, frame_w, TITLEBAR_HEIGHT };
    xcb_poly_fill_rectangle(c, cl->frame, gc, 1, &bg);

    if (visual_type) {
        cairo_surface_t *surface = cairo_xcb_surface_create(c, cl->frame, visual_type, frame_w, TITLEBAR_HEIGHT);
        cairo_t *cr = cairo_create(surface);
        cairo_select_font_face(cr, "sans-serif", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
        cairo_set_font_size(cr, 12);
        cairo_set_source_rgb(cr, 0.9, 0.9, 0.95);

        cairo_save(cr);
        cairo_rectangle(cr, 8, 0, (frame_w > 70) ? frame_w - 70 : 1, TITLEBAR_HEIGHT);
        cairo_clip(cr);
        cairo_move_to(cr, 8, TITLEBAR_HEIGHT - 8);
        cairo_show_text(cr, cl->title);
        cairo_restore(cr);

        cairo_destroy(cr);
        cairo_surface_destroy(surface);
    }

    val = COLOR_CLOSE;
    xcb_change_gc(c, gc, XCB_GC_FOREGROUND, &val);
    xcb_rectangle_t btn_close = { (int16_t)(frame_w - 20), 5, BUTTON_SIZE, BUTTON_SIZE };
    xcb_poly_fill_rectangle(c, cl->frame, gc, 1, &btn_close);

    val = COLOR_MAX;
    xcb_change_gc(c, gc, XCB_GC_FOREGROUND, &val);
    xcb_rectangle_t btn_max = { (int16_t)(frame_w - 38), 5, BUTTON_SIZE, BUTTON_SIZE };
    xcb_poly_fill_rectangle(c, cl->frame, gc, 1, &btn_max);

    val = COLOR_MIN;
    xcb_change_gc(c, gc, XCB_GC_FOREGROUND, &val);
    xcb_rectangle_t btn_min = { (int16_t)(frame_w - 56), 5, BUTTON_SIZE, BUTTON_SIZE };
    xcb_poly_fill_rectangle(c, cl->frame, gc, 1, &btn_min);
    xcb_flush(c);
}

static void handle_configure_request(xcb_configure_request_event_t *e) {
    Client *cl = find_by_window(e->window);

    if (cl) {
        if (e->value_mask & XCB_CONFIG_WINDOW_WIDTH)  cl->w = e->width;
        if (e->value_mask & XCB_CONFIG_WINDOW_HEIGHT) cl->h = e->height;
        if (e->value_mask & XCB_CONFIG_WINDOW_X)      cl->x = e->x;
        if (e->value_mask & XCB_CONFIG_WINDOW_Y)      cl->y = e->y;
        apply_geometry(cl);
        draw_frame(cl);
        xcb_flush(c);
        return;
    }

    uint32_t values[7]; int i = 0; uint16_t mask = 0;
    if (e->value_mask & XCB_CONFIG_WINDOW_X)            { mask |= XCB_CONFIG_WINDOW_X; values[i++] = e->x; }
    if (e->value_mask & XCB_CONFIG_WINDOW_Y)            { mask |= XCB_CONFIG_WINDOW_Y; values[i++] = e->y; }
    if (e->value_mask & XCB_CONFIG_WINDOW_WIDTH)        { mask |= XCB_CONFIG_WINDOW_WIDTH; values[i++] = e->width; }
    if (e->value_mask & XCB_CONFIG_WINDOW_HEIGHT)       { mask |= XCB_CONFIG_WINDOW_HEIGHT; values[i++] = e->height; }
    if (e->value_mask & XCB_CONFIG_WINDOW_BORDER_WIDTH) { mask |= XCB_CONFIG_WINDOW_BORDER_WIDTH; values[i++] = e->border_width; }
    if (e->value_mask & XCB_CONFIG_WINDOW_SIBLING)      { mask |= XCB_CONFIG_WINDOW_SIBLING; values[i++] = e->sibling; }
    if (e->value_mask & XCB_CONFIG_WINDOW_STACK_MODE)   { mask |= XCB_CONFIG_WINDOW_STACK_MODE; values[i++] = e->stack_mode; }
    xcb_configure_window(c, e->window, mask, values);
    xcb_flush(c);
}

static void handle_destroy_notify(xcb_destroy_notify_event_t *e) {
    Client *cl = find_by_window(e->window);
    if (!cl) return;
    if (active_client == cl) active_client = NULL;
    xcb_destroy_window(c, cl->frame);
    remove_client(cl);
    xcb_flush(c);
}

static void handle_property_notify(xcb_property_notify_event_t *e) {
    if (e->atom != XCB_ATOM_WM_NAME) return;
    Client *cl = find_by_window(e->window);
    if (!cl) return;
    fetch_title(cl);
    draw_frame(cl);
}

static void handle_button_press(xcb_button_press_event_t *b) {
    Client *cl = find_by_window(b->event);
    if (cl) {
        focus_and_raise(cl);
        xcb_allow_events(c, XCB_ALLOW_REPLAY_POINTER, XCB_CURRENT_TIME);
        xcb_flush(c);
        return;
    }

    cl = find_by_frame(b->event);
    if (!cl) return;
    focus_and_raise(cl);

    uint16_t frame_w = cl->w + 2 * BORDER_MARGIN;
    uint16_t frame_h = cl->h + TITLEBAR_HEIGHT + BORDER_MARGIN;

    if (b->event_y <= TITLEBAR_HEIGHT) {
        if (b->event_x >= frame_w - 20 && b->event_x <= frame_w - 6) {
            animate_close(cl);
            kill_client_window(cl->window); return;
        } else if (b->event_x >= frame_w - 38 && b->event_x <= frame_w - 24) {
            toggle_maximize(cl); return;
        } else if (b->event_x >= frame_w - 56 && b->event_x <= frame_w - 42) {
            xcb_unmap_window(c, cl->frame); xcb_flush(c); return;
        }
        drag_client = cl;
        drag_start_x = b->root_x; drag_start_y = b->root_y;
        is_dragging = 1;
        return;
    }

    if (b->detail == 3) {
        drag_client = cl;
        drag_start_x = b->root_x; drag_start_y = b->root_y;
        is_resizing = 1;
        resize_edge = EDGE_BOTTOMRIGHT;
        return;
    }

    int on_left = b->event_x <= BORDER_MARGIN;
    int on_right = b->event_x >= frame_w - BORDER_MARGIN;
    int on_bottom = b->event_y >= frame_h - BORDER_MARGIN;

    int edge = EDGE_NONE;
    if (on_left && on_bottom) edge = EDGE_BOTTOMLEFT;
    else if (on_right && on_bottom) edge = EDGE_BOTTOMRIGHT;
    else if (on_left) edge = EDGE_LEFT;
    else if (on_right) edge = EDGE_RIGHT;
    else if (on_bottom) edge = EDGE_BOTTOM;

    if (edge != EDGE_NONE) {
        drag_client = cl;
        drag_start_x = b->root_x; drag_start_y = b->root_y;
        is_resizing = 1;
        resize_edge = edge;
    }
}

static void handle_motion(xcb_motion_notify_event_t *m) {
    if (!drag_client) return;
    int16_t dx = m->root_x - drag_start_x;
    int16_t dy = m->root_y - drag_start_y;

    if (is_dragging) {
        drag_client->x += dx; drag_client->y += dy;
        uint32_t pos[2] = { (uint32_t)(int32_t)drag_client->x, (uint32_t)(int32_t)drag_client->y };
        xcb_configure_window(c, drag_client->frame, XCB_CONFIG_WINDOW_X | XCB_CONFIG_WINDOW_Y, pos);
    } else if (is_resizing) {
        int new_w = drag_client->w, new_h = drag_client->h;
        int new_x = drag_client->x, new_y = drag_client->y;

        if (resize_edge == EDGE_RIGHT || resize_edge == EDGE_BOTTOMRIGHT) new_w += dx;
        if (resize_edge == EDGE_LEFT || resize_edge == EDGE_BOTTOMLEFT) { new_w -= dx; new_x += dx; }
        if (resize_edge == EDGE_BOTTOM || resize_edge == EDGE_BOTTOMLEFT || resize_edge == EDGE_BOTTOMRIGHT) new_h += dy;

        if (new_w < MIN_SIZE) { if (resize_edge == EDGE_LEFT || resize_edge == EDGE_BOTTOMLEFT) new_x = drag_client->x; new_w = drag_client->w; }
        if (new_h < MIN_SIZE) new_h = drag_client->h;

        drag_client->w = new_w; drag_client->h = new_h; drag_client->x = new_x; drag_client->y = new_y;
        apply_geometry(drag_client);
        draw_frame(drag_client);
    }
    drag_start_x = m->root_x; drag_start_y = m->root_y;
    xcb_flush(c);
}

int main(void) {
    int screen_num;
    c = xcb_connect(NULL, &screen_num);
    if (xcb_connection_has_error(c)) return 1;

    xcb_screen_iterator_t iter = xcb_setup_roots_iterator(xcb_get_setup(c));
    for (int i = 0; i < screen_num; i++) xcb_screen_next(&iter);
    screen = iter.data;
    visual_type = find_visual_type(screen);

    gc = xcb_generate_id(c);
    xcb_create_gc(c, gc, screen->root, 0, NULL);

    {
        xcb_font_t cursor_font = xcb_generate_id(c);
        xcb_open_font(c, cursor_font, strlen("cursor"), "cursor");
        default_cursor = xcb_generate_id(c);
        xcb_create_glyph_cursor(c, default_cursor, cursor_font, cursor_font,
                                 68, 69, 0, 0, 0, 0xffff, 0xffff, 0xffff);
        xcb_close_font(c, cursor_font);
        uint32_t cursor_val[1] = { default_cursor };
        xcb_change_window_attributes(c, screen->root, XCB_CW_CURSOR, cursor_val);
    }

    signal(SIGCHLD, SIG_IGN);

    keysyms = xcb_key_symbols_alloc(c);
    uint16_t mods[] = { 0, XCB_MOD_MASK_LOCK, XCB_MOD_MASK_2, XCB_MOD_MASK_LOCK | XCB_MOD_MASK_2 };

    xcb_keycode_t *kc = xcb_key_symbols_get_keycode(keysyms, 0xffeb);
    if (kc) {
        super_keycode = kc[0];
        free(kc);
        for (int m = 0; m < 4; m++)
            xcb_grab_key(c, 1, screen->root, mods[m], super_keycode, XCB_GRAB_MODE_ASYNC, XCB_GRAB_MODE_ASYNC);
    }

    for (size_t h = 0; h < NUM_HOTKEYS; h++) {
        xcb_keycode_t *hkc = xcb_key_symbols_get_keycode(keysyms, hotkeys[h].keysym);
        if (hkc) {
            hotkeys[h].keycode = hkc[0];
            free(hkc);
            for (int m = 0; m < 4; m++)
                xcb_grab_key(c, 1, screen->root, mods[m], hotkeys[h].keycode, XCB_GRAB_MODE_ASYNC, XCB_GRAB_MODE_ASYNC);
        }
    }

    uint32_t values[1] = { XCB_EVENT_MASK_SUBSTRUCTURE_REDIRECT | XCB_EVENT_MASK_SUBSTRUCTURE_NOTIFY };
    xcb_void_cookie_t cookie = xcb_change_window_attributes_checked(c, screen->root, XCB_CW_EVENT_MASK, values);
    xcb_generic_error_t *err = xcb_request_check(c, cookie);
    if (err) { fprintf(stderr, "another WM is running\n"); free(err); return 1; }

    xcb_flush(c);
    printf("vwin running on %dx%d\n", screen->width_in_pixels, screen->height_in_pixels);

    xcb_generic_event_t *ev;
    while ((ev = xcb_wait_for_event(c))) {
        switch (ev->response_type & ~0x80) {
            case XCB_MAP_REQUEST:
                frame_window(((xcb_map_request_event_t *)ev)->window);
                break;
            case XCB_CONFIGURE_REQUEST:
                handle_configure_request((xcb_configure_request_event_t *)ev);
                break;
            case XCB_DESTROY_NOTIFY:
                handle_destroy_notify((xcb_destroy_notify_event_t *)ev);
                break;
            case XCB_PROPERTY_NOTIFY:
                handle_property_notify((xcb_property_notify_event_t *)ev);
                break;
            case XCB_KEY_PRESS: {
                xcb_key_press_event_t *k = (xcb_key_press_event_t *)ev;
                if (super_keycode && k->detail == super_keycode) { spawn_launcher(); break; }
                for (size_t h = 0; h < NUM_HOTKEYS; h++) {
                    if (hotkeys[h].keycode && k->detail == hotkeys[h].keycode) { run_shell(hotkeys[h].cmd); break; }
                }
                break;
            }
            case XCB_EXPOSE: {
                Client *cl = find_by_frame(((xcb_expose_event_t *)ev)->window);
                if (cl) draw_frame(cl);
                break;
            }
            case XCB_BUTTON_PRESS:
                handle_button_press((xcb_button_press_event_t *)ev);
                break;
            case XCB_MOTION_NOTIFY:
                handle_motion((xcb_motion_notify_event_t *)ev);
                break;
            case XCB_BUTTON_RELEASE:
                is_dragging = 0; is_resizing = 0; resize_edge = EDGE_NONE; drag_client = NULL;
                break;
        }
        free(ev);
    }
    xcb_disconnect(c);
    return 0;
}
