import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 640
    height: 720
    visible: true
    title: "FormatConverter" + (typeof appVersion !== "undefined" && appVersion ? " v" + appVersion : "")

    property bool advancedOpen: false

    function collectOptions() {
        return {
            "bitrate": bitrateBox.currentValue,
            "sampleRate": sampleRateBox.currentValue,
            "channels": channelsBox.currentValue,
            "volumeDb": volumeSpin.value,
            "normalize": normalizeCheck.checked,
            "trimStart": trimStartField.text,
            "trimEnd": trimEndField.text
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Label {
            text: "파일 포맷 변환기"
            font.pixelSize: 22
            font.bold: true
        }

        // ---- 드래그앤드롭 영역 ----
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 130
            radius: 10
            color: dropArea.containsDrag ? "#e8f0fe" : "#f5f5f7"
            border.color: dropArea.containsDrag ? "#4285f4" : "#cccccc"
            border.width: 2

            DropArea {
                id: dropArea
                anchors.fill: parent
                onDropped: (drop) => {
                    if (drop.hasUrls)
                        backend.addUrls(drop.urls)
                }
            }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 6
                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: "⬇  여기로 파일을 끌어다 놓으세요"
                    font.pixelSize: 16
                    color: "#555"
                }
                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: "영상(mp4 등) → 음원(mp3 등) 변환"
                    font.pixelSize: 12
                    color: "#999"
                }
            }
        }

        // ---- 파일 목록 ----
        Frame {
            Layout.fillWidth: true
            Layout.preferredHeight: 140
            ListView {
                id: fileList
                anchors.fill: parent
                clip: true
                model: backend.files
                delegate: Label {
                    width: fileList.width
                    text: "• " + modelData
                    elide: Text.ElideMiddle
                    padding: 4
                }
            }
        }

        // ---- 출력 포맷 ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Label { text: "출력 포맷:"; font.pixelSize: 14 }
            ComboBox {
                id: outputBox
                Layout.preferredWidth: 140
                model: backend.outputFormats
                onActivated: backend.setOutputFormat(currentText)
                onModelChanged: if (count > 0) backend.setOutputFormat(currentText)
            }
            Item { Layout.fillWidth: true }
            Button {
                text: advancedOpen ? "고급 옵션 ▲" : "고급 옵션 ▼"
                onClicked: advancedOpen = !advancedOpen
            }
        }

        // ---- 고급 옵션 ----
        GroupBox {
            Layout.fillWidth: true
            title: "고급 옵션"
            visible: advancedOpen
            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 16
                rowSpacing: 8

                Label { text: "비트레이트" }
                ComboBox {
                    id: bitrateBox
                    Layout.fillWidth: true
                    textRole: "text"
                    valueRole: "value"
                    currentIndex: 1
                    model: [
                        { text: "128 kbps", value: "128k" },
                        { text: "192 kbps", value: "192k" },
                        { text: "256 kbps", value: "256k" },
                        { text: "320 kbps", value: "320k" }
                    ]
                }

                Label { text: "샘플레이트" }
                ComboBox {
                    id: sampleRateBox
                    Layout.fillWidth: true
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: 0 },
                        { text: "44100 Hz", value: 44100 },
                        { text: "48000 Hz", value: 48000 },
                        { text: "22050 Hz", value: 22050 }
                    ]
                }

                Label { text: "채널" }
                ComboBox {
                    id: channelsBox
                    Layout.fillWidth: true
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: 0 },
                        { text: "스테레오", value: 2 },
                        { text: "모노", value: 1 }
                    ]
                }

                Label { text: "볼륨 (dB)" }
                SpinBox {
                    id: volumeSpin
                    Layout.fillWidth: true
                    from: -30; to: 30; value: 0
                }

                Label { text: "정규화" }
                CheckBox {
                    id: normalizeCheck
                    text: "볼륨 자동 정규화 (loudnorm)"
                }

                Label { text: "구간 자르기 (초)" }
                RowLayout {
                    Layout.fillWidth: true
                    TextField {
                        id: trimStartField
                        Layout.fillWidth: true
                        placeholderText: "시작 (예: 30)"
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                    }
                    Label { text: "~" }
                    TextField {
                        id: trimEndField
                        Layout.fillWidth: true
                        placeholderText: "끝 (예: 90)"
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }

        // ---- 진행률 ----
        ProgressBar {
            Layout.fillWidth: true
            from: 0; to: 1
            value: backend.progress
        }
        Label {
            Layout.fillWidth: true
            text: backend.status
            color: "#444"
            elide: Text.ElideRight
        }

        // ---- 실행 버튼 ----
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Button {
                text: "목록 비우기"
                enabled: !backend.busy
                onClicked: backend.clearFiles()
            }
            Item { Layout.fillWidth: true }
            Button {
                visible: backend.busy
                text: "취소"
                onClicked: backend.cancel()
            }
            Button {
                text: backend.busy ? "변환 중…" : "변환 시작"
                enabled: !backend.busy && backend.files.length > 0
                highlighted: true
                onClicked: backend.start(win.collectOptions())
            }
        }
    }
}
