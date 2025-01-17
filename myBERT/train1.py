import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from sklearn.metrics import f1_score

class BERTBiLSTM(nn.Module):
    def __init__(self, bert_path, num_labels, hidden_size, lstm_hidden_size):
        super(BERTBiLSTM, self).__init__()
        self.bert = BertModel.from_pretrained(bert_path)
        self.lstm = nn.LSTM(self.bert.config.hidden_size, lstm_hidden_size, num_layers=1, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(2*lstm_hidden_size, num_labels)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state
        lstm_output, (h_n, c_n) = self.lstm(sequence_output)
        h_n = torch.cat((h_n[-2,:,:], h_n[-1,:,:]), dim=1)
        h_n = self.dropout(h_n)
        logits = self.classifier(h_n)
        return logits

def train(model, train_dataloader, val_dataloader=None, epochs=4, evaluation=False):
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        train_loss = 0
        train_f1 = 0

        model.train()
        for batch in train_dataloader:
            batch = tuple(t.to(device) for t in batch)
            input_ids, attention_mask, labels = batch

            optimizer.zero_grad()
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_f1 += f1_score(labels.cpu().numpy(), logits.argmax(1).cpu().numpy(), average='weighted')

        if evaluation:
            val_loss, val_f1 = evaluate(model, val_dataloader)
            print('Epoch: {}/{} | Train Loss: {:.3f} | Train F1 Score: {:.3f} | Val Loss: {:.3f} | Val F1 Score: {:.3f}'
                  .format(epoch+1, epochs, train_loss/len(train_dataloader), train_f1/len(train_dataloader), val_loss, val_f1))
        else:
            print('Epoch: {}/{} | Train Loss: {:.3f} | Train F1 Score: {:.3f}'
                  .format(epoch+1, epochs, train_loss/len(train_dataloader), train_f1/len(train_dataloader)))

    return model

# 定义训练数据和标签
train_texts = ['第一篇文本', '第二篇文本', ...]
train_labels = [0, 1, ...] # 标签应该是整


def convert_to_text_label(filename:str):
    with open(filename) as fs:
        text = []
        label = []
        lines = fs.readlines()
        for line in lines:
            split_cnt = line.split('\t')
            text.append(split_cnt[0])
            label.append(int(split_cnt[1]))
    return text,label

train_texts = []
train_labels = []

new_text,new_label = convert_to_text_label("./myBERT/train.txt")
train_texts.extend(new_text)
train_labels.extend(new_label)
new_text,new_label = convert_to_text_label("./myBERT/dev.txt")
train_texts.extend(new_text)
train_labels.extend(new_label)
train_labels = [int(ids)-2 for ids in train_labels]

# 定义tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')

# 将文本转换为token和input_mask
train_input_ids = []
train_attention_masks = []
for text in train_texts:
    encoded_dict = tokenizer.encode_plus(text, add_special_tokens=True, max_length=128, pad_to_max_length=True, return_attention_mask=True, return_tensors='pt')
    train_input_ids.append(encoded_dict['input_ids'])
    train_attention_masks.append(encoded_dict['attention_mask'])

train_input_ids = torch.cat(train_input_ids, dim=0)
train_attention_masks = torch.cat(train_attention_masks, dim=0)
train_labels = torch.tensor(train_labels)

# 定义训练数据集和数据加载器
train_dataset = TensorDataset(train_input_ids, train_attention_masks, train_labels)
train_sampler = RandomSampler(train_dataset)
train_dataloader = DataLoader(train_dataset, sampler=train_sampler, batch_size=32)


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = BERTBiLSTM('bert-base-chinese', 10, 768, 256).to(device)
model = train(model, train_dataloader, epochs=4, evaluation=False)

torch.save(model,"myModel/bilstm_bert.pt")
from sklearn.metrics import confusion_matrix, classification_report

def evaluate(model, dataloader):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    y_true = []
    y_pred = []
    with torch.no_grad():
        for input_ids, attention_masks, labels in dataloader:
            input_ids = input_ids.to(device)
            attention_masks = attention_masks.to(device)
            labels = labels.to(device)

            outputs = model(input_ids, attention_masks)
            _, predicted = torch.max(outputs, dim=1)
            y_true.extend(labels.tolist())
            y_pred.extend(predicted.tolist())

    target_names = ["婚恋交友", "假冒身份" ,"钓鱼网站", "冒充公检法" ,"平台诈骗" ,"招聘兼职" ,"杀猪盘" ,"博彩赌博" ,"信贷理财" ,"刷单诈骗" ]
    print('Classification Report:')
    print(classification_report(y_true, y_pred, target_names=target_names))
    print('Confusion Matrix:')
    print(confusion_matrix(y_true, y_pred))


test_texts,test_labels = convert_to_text_label("./myBERT/test.txt")




# 将文本转换为token和input_mask
test_input_ids = []
test_attention_masks = []
for text in test_texts:
    encoded_dict = tokenizer.encode_plus(text, add_special_tokens=True, max_length=128, pad_to_max_length=True, return_attention_mask=True, return_tensors='pt')
    test_input_ids.append(encoded_dict['input_ids'])
    test_attention_masks.append(encoded_dict['attention_mask'])

test_input_ids = torch.cat(test_input_ids, dim=0)
test_attention_masks = torch.cat(test_attention_masks, dim=0)

test_labels = [int(ids)-2 for ids in test_labels]
test_labels = torch.tensor(test_labels)



# 定义测试数据集和数据加载器
test_dataset = TensorDataset(test_input_ids, test_attention_masks, test_labels)
test_sampler = RandomSampler(test_dataset)
test_dataloader = DataLoader(test_dataset, sampler=test_sampler, batch_size=32)

evaluate(model,test_dataloader)