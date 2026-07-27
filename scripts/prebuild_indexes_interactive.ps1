#!/usr/bin/env powershell
# 一键预生成图索引脚本
# 用法：powershell -File scripts/prebuild_indexes_interactive.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "LocAgent 图索引预生成工具" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# 检查环境
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[检查环境]" -ForegroundColor Yellow
Write-Host "  工作目录: $Root"

# 检查 Python
try {
    $pythonCmd = Get-Command python -ErrorAction Stop
    Write-Host "  Python: $($pythonCmd.Source)" -ForegroundColor Green
} catch {
    Write-Host "  错误: 未找到 Python" -ForegroundColor Red
    exit 1
}

# 检查 LocAgent
if (-not (Test-Path "LocAgent")) {
    Write-Host "  错误: 未找到 LocAgent 目录" -ForegroundColor Red
    exit 1
}
Write-Host "  LocAgent: 已就绪" -ForegroundColor Green

Write-Host ""

# 询问用户
Write-Host "[选择预生成方式]" -ForegroundColor Yellow
Write-Host "  1. 生成 5 个样本的图索引（推荐，约30分钟）"
Write-Host "  2. 生成 10 个样本的图索引（约60分钟）"
Write-Host "  3. 生成全部样本的图索引（约24小时）"
Write-Host "  4. 自定义数量"
Write-Host "  5. 退出"
Write-Host ""

$choice = Read-Host "请选择 (1-5)"

switch ($choice) {
    "1" {
        $n_limit = 5
    }
    "2" {
        $n_limit = 10
    }
    "3" {
        $n_limit = $null
    }
    "4" {
        $n_limit = [int](Read-Host "输入样本数量")
    }
    "5" {
        Write-Host "已取消" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "无效选择" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[开始预生成]" -ForegroundColor Yellow
Write-Host "  样本数量: $(if ($n_limit) { $n_limit } else { '全部' })"
Write-Host ""

# 运行 Python 脚本
$scriptPath = "scripts\prebuild_graph_indexes.py"

if ($n_limit) {
    $cmd = "python $scriptPath --eval_n_limit $n_limit"
} else {
    $cmd = "python $scriptPath"
}

Write-Host "执行命令: $cmd" -ForegroundColor Gray
Write-Host ""

# 执行
try {
    Invoke-Expression $cmd
    Write-Host ""
    Write-Host "==================================" -ForegroundColor Green
    Write-Host "✓ 图索引预生成完成！" -ForegroundColor Green
    Write-Host "==================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步：" -ForegroundColor Cyan
    Write-Host "  powershell -File scripts\run_locagent_verified_10.ps1" -ForegroundColor White
} catch {
    Write-Host ""
    Write-Host "==================================" -ForegroundColor Red
    Write-Host "✗ 预生成失败" -ForegroundColor Red
    Write-Host "==================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "错误: $_" -ForegroundColor Red
    exit 1
}