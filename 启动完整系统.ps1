# -*- coding: utf-8 -*-
# 启动完整科研多Agent系统的PowerShell脚本

Write-Host "===========================================" -ForegroundColor Green
Write-Host "科研多Agent系统 - 完整系统启动脚本" -ForegroundColor Green  
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# 检查是否在正确的目录
if (-not (Test-Path "真实Agent智能服务器.py") -or -not (Test-Path "frontend")) {
    Write-Host "❌ 错误：项目文件不完整" -ForegroundColor Red
    Write-Host "请确保在项目根目录运行此脚本" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "🔍 系统环境检查..." -ForegroundColor Blue
Write-Host ""

# 检查Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python未安装或未添加到PATH" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查前端HTML文件
if (Test-Path "frontend/index.html") {
    Write-Host "✅ 前端HTML界面: 就绪" -ForegroundColor Green
} else {
    Write-Host "❌ 前端HTML文件未找到" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "🚀 启动系统组件..." -ForegroundColor Green
Write-Host ""

# 启动后端服务器
Write-Host "📡 启动真实Agent智能服务器 (端口 8000)..." -ForegroundColor Blue

# 启动后端服务器作业
$backendJob = Start-Job -ScriptBlock {
    param($projectPath)
    Set-Location $projectPath
    python "真实Agent智能服务器.py"
} -ArgumentList (Get-Location)

Write-Host "✅ 后端服务器启动中..." -ForegroundColor Green

# 等待后端启动
Write-Host "⏳ 等待后端服务器初始化..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# 测试后端连接
$backendReady = $false
$maxRetries = 10
$retryCount = 0

while (-not $backendReady -and $retryCount -lt $maxRetries) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -TimeoutSec 3
        $backendReady = $true
        Write-Host "✅ 后端服务器就绪 - 状态: $($response.status)" -ForegroundColor Green
    }
    catch {
        $retryCount++
        Write-Host "⏳ 等待后端服务器... ($retryCount/$maxRetries)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $backendReady) {
    Write-Host "❌ 后端服务器启动失败或超时" -ForegroundColor Red
    Stop-Job $backendJob
    Remove-Job $backendJob
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "🌐 前端界面通过后端托管，无需单独启动" -ForegroundColor Blue
Write-Host ""

Write-Host "===========================================" -ForegroundColor Green
Write-Host "🎉 系统启动完成！" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 系统访问地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📡 后端API地址:   http://localhost:8000/api/" -ForegroundColor Cyan
Write-Host "📚 API文档地址:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 使用说明:" -ForegroundColor Yellow
Write-Host "   1. 在浏览器中打开: http://localhost:8000" -ForegroundColor White
Write-Host "   2. 使用真实Agent智能科研系统界面" -ForegroundColor White
Write-Host "   3. 输入研究问题进行多Agent协作分析" -ForegroundColor White
Write-Host "   4. 查看实时Agent协作过程和结果" -ForegroundColor White
Write-Host ""
Write-Host "🔧 管理命令:" -ForegroundColor Yellow
Write-Host "   按 'q' + Enter 停止系统" -ForegroundColor White
Write-Host "   按 's' + Enter 查看状态" -ForegroundColor White
Write-Host "   按 't' + Enter 测试API" -ForegroundColor White
Write-Host "   按 'h' + Enter 查看帮助" -ForegroundColor White
Write-Host ""

# 自动在浏览器中打开界面
Write-Host "🔄 正在自动打开系统界面..." -ForegroundColor Blue
Start-Process "http://localhost:8000"

# 监控和管理循环
while ($true) {
    $input = Read-Host "命令"
    
    switch ($input.ToLower()) {
        "q" {
            Write-Host ""
            Write-Host "🔄 正在停止系统..." -ForegroundColor Yellow
            
            # 停止作业
            Stop-Job $backendJob -ErrorAction SilentlyContinue
            Remove-Job $backendJob -ErrorAction SilentlyContinue
            
            Write-Host "✅ 系统已停止" -ForegroundColor Green
            exit 0
        }
        "s" {
            Write-Host ""
            Write-Host "📊 系统状态:" -ForegroundColor Blue
            Write-Host "   后端作业: $($backendJob.State)" -ForegroundColor White
            
            # 测试连接
            try {
                $healthCheck = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -TimeoutSec 2
                Write-Host "   后端连接: ✅ 正常 - $($healthCheck.message)" -ForegroundColor Green
                Write-Host "   系统模式: $($healthCheck.system_mode)" -ForegroundColor White
                Write-Host "   版本信息: $($healthCheck.version)" -ForegroundColor White
            }
            catch {
                Write-Host "   后端连接: ❌ 异常" -ForegroundColor Red
            }
            Write-Host ""
        }
        "t" {
            Write-Host ""
            Write-Host "🧪 执行API测试..." -ForegroundColor Blue
            try {
                # 测试健康检查
                $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -TimeoutSec 5
                Write-Host "   健康检查: ✅ $($health.status)" -ForegroundColor Green
                
                # 测试系统状态
                $status = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/status" -Method Get -TimeoutSec 5
                Write-Host "   系统状态: ✅ 就绪" -ForegroundColor Green
                
                # 测试简单研究请求
                $testBody = @{query="测试Agent系统连通性"; priority="normal"} | ConvertTo-Json
                $research = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/research/submit" -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 10
                if ($research.success) {
                    Write-Host "   研究API: ✅ 正常 - 会话ID: $($research.session_id)" -ForegroundColor Green
                } else {
                    Write-Host "   研究API: ⚠️ 有问题" -ForegroundColor Yellow
                }
            }
            catch {
                Write-Host "   API测试: ❌ 失败 - $($_.Exception.Message)" -ForegroundColor Red
            }
            Write-Host ""
        }
        "h" {
            Write-Host ""
            Write-Host "📖 帮助信息:" -ForegroundColor Blue
            Write-Host "   q - 退出系统" -ForegroundColor White
            Write-Host "   s - 查看状态" -ForegroundColor White
            Write-Host "   t - 测试API功能" -ForegroundColor White
            Write-Host "   h - 显示帮助" -ForegroundColor White
            Write-Host ""
            Write-Host "🌐 访问地址:" -ForegroundColor Blue
            Write-Host "   主界面: http://localhost:8000" -ForegroundColor Cyan
            Write-Host "   API文档: http://localhost:8000/docs" -ForegroundColor Cyan
            Write-Host "   健康检查: http://localhost:8000/api/health" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "🎯 系统特性:" -ForegroundColor Blue
            Write-Host "   • 真实Agent智能协作系统" -ForegroundColor White
            Write-Host "   • 实时WebSocket通信" -ForegroundColor White
            Write-Host "   • 黑板协作机制" -ForegroundColor White
            Write-Host "   • 可视化Agent状态监控" -ForegroundColor White
            Write-Host ""
        }
        default {
            Write-Host "❓ 未知命令。输入 'h' 查看帮助" -ForegroundColor Yellow
        }
    }
} 