from pathlib import Path

content = r"""{% extends "admin_panel/base_new.html" %}
{% load static %}
{% block title %}Inventory{% endblock %}
{% block heading %}Inventory{% endblock %}
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/admin-panel-inventory.css' %}">
{% endblock %}
{% block content %}
<div class="page-head-inv">
    <div>
        <h1>Inventory</h1>
        <motion class="sub">Manage your live catalogue and past sales</motion>
    </div>
    <a href="{% url 'admin_panel:car_add' %}" class="btn-primary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
        Add Vehicle
    </a>
</div>

<div id="ap-inventory-partial" data-ap-partial-root>
{% include "admin_panel/partials/car_list_partial.html" %}
</div>
{% endblock %}
"""
content = content.replace("motion", "div")
Path("templates/admin_panel/car_list_new.html").write_text(content, encoding="utf-8")
print("ok")
