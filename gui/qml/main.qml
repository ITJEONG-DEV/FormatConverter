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
            "trimEnd": trimEndField.text,
            "videoResolution": resolutionBox.currentValue,
            "videoFps": fpsBox.currentValue,
            "videoQuality": qualityBox.currentValue,
            "imageResolution": imgResolutionBox.currentValue,
            "imageQuality": imgQualityBox.currentValue
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
                    text: "영상 → 영상/음원 · 음원 → 음원 · 이미지 → 이미지"
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

                Label {
                    text: "비트레이트"
                    visible: backend.outputKind !== "image"
                }
                ComboBox {
                    id: bitrateBox
                    Layout.fillWidth: true
                    visible: backend.outputKind !== "image"
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

                // ----- 오디오 전용 (음원 출력일 때) -----
                Label {
                    text: "샘플레이트"
                    visible: backend.outputKind !== "video"
                }
                ComboBox {
                    id: sampleRateBox
                    Layout.fillWidth: true
                    visible: backend.outputKind !== "video"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: 0 },
                        { text: "44100 Hz", value: 44100 },
                        { text: "48000 Hz", value: 48000 },
                        { text: "22050 Hz", value: 22050 }
                    ]
                }

                Label {
                    text: "채널"
                    visible: backend.outputKind !== "video"
                }
                ComboBox {
                    id: channelsBox
                    Layout.fillWidth: true
                    visible: backend.outputKind !== "video"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: 0 },
                        { text: "스테레오", value: 2 },
                        { text: "모노", value: 1 }
                    ]
                }

                Label {
                    text: "볼륨 (dB)"
                    visible: backend.outputKind !== "video"
                }
                SpinBox {
                    id: volumeSpin
                    Layout.fillWidth: true
                    visible: backend.outputKind !== "video"
                    from: -30; to: 30; value: 0
                }

                Label {
                    text: "정규화"
                    visible: backend.outputKind !== "video"
                }
                CheckBox {
                    id: normalizeCheck
                    visible: backend.outputKind !== "video"
                    text: "볼륨 자동 정규화 (loudnorm)"
                }

                // ----- 비디오 전용 (영상 출력일 때) -----
                Label {
                    text: "해상도"
                    visible: backend.outputKind === "video"
                }
                ComboBox {
                    id: resolutionBox
                    Layout.fillWidth: true
                    visible: backend.outputKind === "video"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: "" },
                        { text: "1080p", value: "1080" },
                        { text: "720p", value: "720" },
                        { text: "480p", value: "480" }
                    ]
                }

                Label {
                    text: "프레임레이트"
                    visible: backend.outputKind === "video"
                }
                ComboBox {
                    id: fpsBox
                    Layout.fillWidth: true
                    visible: backend.outputKind === "video"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: 0 },
                        { text: "60 fps", value: 60 },
                        { text: "30 fps", value: 30 },
                        { text: "24 fps", value: 24 }
                    ]
                }

                Label {
                    text: "화질"
                    visible: backend.outputKind === "video"
                }
                ComboBox {
                    id: qualityBox
                    Layout.fillWidth: true
                    visible: backend.outputKind === "video"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "자동", value: 0 },
                        { text: "높은 화질 (CRF 18)", value: 18 },
                        { text: "보통 (CRF 23)", value: 23 },
                        { text: "작은 용량 (CRF 28)", value: 28 }
                    ]
                }

                // ----- 이미지 전용 (이미지 출력일 때) -----
                Label {
                    text: "해상도"
                    visible: backend.outputKind === "image"
                }
                ComboBox {
                    id: imgResolutionBox
                    Layout.fillWidth: true
                    visible: backend.outputKind === "image"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "원본 유지", value: "" },
                        { text: "높이 1080px", value: "1080" },
                        { text: "높이 720px", value: "720" },
                        { text: "높이 480px", value: "480" }
                    ]
                }

                Label {
                    text: "품질 (jpg/webp)"
                    visible: backend.outputKind === "image"
                }
                ComboBox {
                    id: imgQualityBox
                    Layout.fillWidth: true
                    visible: backend.outputKind === "image"
                    textRole: "text"
                    valueRole: "value"
                    model: [
                        { text: "기본", value: 0 },
                        { text: "최고 (95)", value: 95 },
                        { text: "높음 (85)", value: 85 },
                        { text: "보통 (75)", value: 75 }
                    ]
                }

                // ----- 구간 자르기 (영상·음원만) -----
                Label {
                    text: "구간 자르기 (초)"
                    visible: backend.outputKind !== "image"
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: backend.outputKind !== "image"
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

    // ---- 자동 업데이트 다이얼로그 ----
    Popup {
        id: updateDialog
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose
        visible: updater.available
        anchors.centerIn: Overlay.overlay
        width: 440
        padding: 20

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            Label {
                text: "새 버전 " + updater.latestVersion + " 이(가) 있습니다"
                font.pixelSize: 18
                font.bold: true
            }
            Label {
                text: "현재 버전: v" + appVersion
                color: "#666"
            }

            Frame {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                ScrollView {
                    anchors.fill: parent
                    clip: true
                    TextArea {
                        readOnly: true
                        wrapMode: TextArea.Wrap
                        text: updater.changes
                    }
                }
            }

            ProgressBar {
                Layout.fillWidth: true
                visible: updater.busy
                from: 0; to: 100
                value: updater.progress
            }
            Label {
                Layout.fillWidth: true
                text: updater.message
                visible: updater.message !== ""
                color: "#444"
                wrapMode: Label.Wrap
            }

            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: "나중에"
                    enabled: !updater.busy
                    onClicked: updater.dismiss()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: updater.busy ? "설치 중…" : "지금 업데이트"
                    highlighted: true
                    enabled: !updater.busy
                    onClicked: updater.apply()
                }
            }
        }
    }
}
